"""
Credentials of a vantage6 hub, which are stored in Kubernetes secrets instead of in the
hub configuration file.
"""

import secrets
from dataclasses import dataclass, field
from urllib.parse import quote

from vantage6.common.globals import APPNAME, InstanceType

# Defaults of the HQ configuration template, which the RabbitMQ URI must match
DEFAULT_RABBITMQ_USERNAME = "rabbitmquser"
DEFAULT_RABBITMQ_VHOST = "/vantage6"
DEFAULT_KEYCLOAK_ADMIN_USERNAME = "admin"


@dataclass
class HubSecretNames:
    """Names of the Kubernetes secrets with the credentials of a hub."""

    hq: str
    store: str
    auth_db: str
    realm: str

    @classmethod
    def for_hub(cls, name: str, system_folders: bool) -> "HubSecretNames":
        """
        Get the secret names for a hub.

        Parameters
        ----------
        name : str
            Name of the hub configuration
        system_folders : bool
            Whether the configuration is stored in the system folders

        Returns
        -------
        HubSecretNames
            The secret names, prefixed with the Helm release name of the hub
        """
        prefix = hub_release_name(name, system_folders)
        return cls(
            hq=f"{prefix}-hq-credentials",
            store=f"{prefix}-store-credentials",
            auth_db=f"{prefix}-auth-db-credentials",
            realm=f"{prefix}-realm-credentials",
        )


@dataclass
class HubCredentials:
    """Credentials collected while creating a hub configuration."""

    admin_password: str
    admin_client_secret: str
    admin_username: str = DEFAULT_KEYCLOAK_ADMIN_USERNAME
    auth_db: dict[str, str] = field(default_factory=dict)
    smtp_password: str | None = None
    hq_database_uri: str | None = None
    rabbitmq_password: str | None = None
    store_database_uri: str | None = None


def hub_release_name(name: str, system_folders: bool) -> str:
    """
    Get the Helm release name of a hub, as used by `v6 hub start`.

    Parameters
    ----------
    name : str
        Name of the hub configuration
    system_folders : bool
        Whether the configuration is stored in the system folders

    Returns
    -------
    str
        The Helm release name
    """
    scope = "system" if system_folders else "user"
    return f"{APPNAME}-{name}-{scope}-{InstanceType.HUB.value}"


def extract_auth_credentials(
    config: dict, credentials: HubCredentials, secret_names: HubSecretNames
) -> dict:
    """
    Move the credentials out of the auth configuration and reference the secrets.

    Parameters
    ----------
    config : dict
        Auth configuration. The credentials are removed from it.
    credentials : HubCredentials
        Collected credentials, updated with those of the auth configuration
    secret_names : HubSecretNames
        Names of the secrets of the hub

    Returns
    -------
    dict
        The auth configuration without credentials
    """
    database = config["database"]
    credentials.auth_db = {
        "username": database.pop("username"),
        "password": database.pop("password"),
    }
    database["existingSecret"] = secret_names.auth_db
    smtp = config["keycloak"].get("smtpServer") or {}
    credentials.smtp_password = smtp.pop("password", None)
    config["keycloak"]["realmImportSecret"] = secret_names.realm
    return config


def extract_hq_credentials(
    config: dict, credentials: HubCredentials, secret_names: HubSecretNames
) -> dict:
    """
    Move the credentials out of the HQ configuration and reference the secret.

    Parameters
    ----------
    config : dict
        HQ configuration. The credentials are removed from it.
    credentials : HubCredentials
        Collected credentials, updated with those of the HQ configuration
    secret_names : HubSecretNames
        Names of the secrets of the hub

    Returns
    -------
    dict
        The HQ configuration without credentials
    """
    credentials.hq_database_uri = config["database"].pop("uri")
    credentials.rabbitmq_password = config["rabbitmq"].pop("password")
    config["hq"]["existingSecret"] = secret_names.hq
    return config


def extract_store_credentials(
    config: dict, credentials: HubCredentials, secret_names: HubSecretNames
) -> dict:
    """
    Move the credentials out of the algorithm store configuration and reference the
    secret.

    Parameters
    ----------
    config : dict
        Algorithm store configuration. The credentials are removed from it.
    credentials : HubCredentials
        Collected credentials, updated with those of the store configuration
    secret_names : HubSecretNames
        Names of the secrets of the hub

    Returns
    -------
    dict
        The algorithm store configuration without credentials
    """
    credentials.store_database_uri = config["database"].pop("uri")
    config["store"]["existingSecret"] = secret_names.store
    return config


def rabbitmq_uri(release_name: str, password: str) -> str:
    """
    Get the URI with which HQ connects to the RabbitMQ service of the hub.

    Parameters
    ----------
    release_name : str
        Helm release name of the hub
    password : str
        RabbitMQ password

    Returns
    -------
    str
        The RabbitMQ URI, with URL-encoded username, password and vhost
    """
    return (
        f"amqp://{quote(DEFAULT_RABBITMQ_USERNAME, safe='')}:{quote(password, safe='')}"
        f"@{release_name}-rabbitmq:5672/{quote(DEFAULT_RABBITMQ_VHOST, safe='')}"
    )


def build_hub_secrets(
    credentials: HubCredentials,
    secret_names: HubSecretNames,
    release_name: str,
    has_store: bool,
) -> dict[str, dict[str, str]]:
    """
    Get the data of the Kubernetes secrets of a hub.

    Parameters
    ----------
    credentials : HubCredentials
        Collected credentials
    secret_names : HubSecretNames
        Names of the secrets of the hub
    release_name : str
        Helm release name of the hub
    has_store : bool
        Whether the hub has an algorithm store

    Returns
    -------
    dict[str, dict[str, str]]
        The data of each secret, by secret name
    """
    keycloak_admin = {
        "KEYCLOAK_ADMIN_PASSWORD": credentials.admin_password,
        "KEYCLOAK_ADMIN_CLIENT_SECRET": credentials.admin_client_secret,
    }
    realm = {
        "admin-password": credentials.admin_password,
        "backend-client-secret": credentials.admin_client_secret,
    }
    if credentials.smtp_password:
        realm["smtp-password"] = credentials.smtp_password
    hub_secrets = {
        secret_names.auth_db: credentials.auth_db,
        secret_names.realm: realm,
        secret_names.hq: {
            **keycloak_admin,
            "V6_JWT_SECRET_KEY": secrets.token_urlsafe(48),
            "V6_DATABASE_URI": credentials.hq_database_uri,
            "V6_RABBITMQ_URI": rabbitmq_uri(
                release_name, credentials.rabbitmq_password
            ),
            "RABBITMQ_PASSWORD": credentials.rabbitmq_password,
        },
    }
    if has_store:
        store = {**keycloak_admin, "V6_DATABASE_URI": credentials.store_database_uri}
        if credentials.smtp_password:
            store["V6_SMTP_PASSWORD"] = credentials.smtp_password
        hub_secrets[secret_names.store] = store
    return hub_secrets
