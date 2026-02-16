import uuid
from typing import Any
from urllib.parse import urlparse

import questionary as q

from vantage6.common import error, info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import create_kubernetes_secret, generate_password
from vantage6.cli.configuration_create import (
    get_external_database_url,
)
from vantage6.cli.globals import APPNAME
from vantage6.cli.hub.utils.enum import AuthCredentials
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.utils_kubernetes import (
    get_core_api_with_ssl_handling,
    replace_localhost_for_k8s,
)


def auth_configuration_questionaire(
    name: str, k8s_cfg: KubernetesConfig, credentials: dict[AuthCredentials, Any]
) -> tuple[dict[str, Any]]:
    """
    Kubernetes-specific questionnaire to generate Helm values for the Keycloak helm
    chart.

    Parameters
    ----------
    name: str
        The name of the authentication service
    k8s_cfg: KubernetesConfig
        The Kubernetes configuration
    credentials: dict[AuthCredentials, Any]
        Dictionary with the credentials for the authentication service. This will be
        updated with the new credentials.

    Returns
    -------
    tuple[dict[str, Any]]
        Dictionary with the configuration for the authentication service
    """
    config = {"keycloak": {}, "database": {}}

    config["keycloak"]["production"] = True

    config = _add_external_database_config(config, k8s_node=k8s_cfg.k8s_node)

    config = _add_keycloak_admin_secret(config, name, k8s_cfg, credentials)

    config["keycloak"]["adminClientSecret"] = _get_admin_client_secret()

    config["keycloak"]["adminPassword"] = _get_admin_password()

    # Add SMTP configuration if requested
    config = _add_smtp_config(config)

    return config


def _get_admin_client_secret() -> str:
    """
    Get the admin client secret.
    """
    provide_secret = q.confirm(
        "Do you want to choose a secret for the Keycloak backend client yourself? ",
        default=False,
    ).unsafe_ask()

    if provide_secret:
        admin_client_secret = q.password(
            "Enter Keycloak admin client secret:"
        ).unsafe_ask()
    else:
        admin_client_secret = generate_password(password_length=32)

    return admin_client_secret


def _get_admin_password() -> str:
    """
    Get the admin password.
    """
    return generate_password()


def _add_smtp_config(config: dict) -> dict:
    """
    Get SMTP server configuration from user.

    Returns
    -------
    dict
        Configuration dict with added SMTP configuration
    """
    configure_smtp = q.confirm(
        "Do you want to configure an SMTP server for email sending?",
        default=False,
    ).unsafe_ask()

    if not configure_smtp:
        return config

    smtp_config = {}

    smtp_config["host"] = q.text(
        "SMTP server hostname:",
        default="smtp.example.com",
    ).unsafe_ask()

    smtp_config["port"] = q.text(
        "SMTP server port (usually 587 for STARTTLS, 465 for SSL):",
        default="587",
    ).unsafe_ask()

    # SSL and STARTTLS are typically mutually exclusive
    # Port 465 usually uses SSL, port 587 usually uses STARTTLS
    if smtp_config["port"] == "587":
        encryption_type = "starttls"
    elif smtp_config["port"] == "465":
        encryption_type = "ssl"
    else:
        encryption_type = q.select(
            "SMTP encryption:",
            choices=[
                "starttls",
                "ssl",
                "none",
            ],
            default="starttls",
        ).unsafe_ask()

    if encryption_type == "starttls":
        smtp_config["ssl"] = "false"
        smtp_config["starttls"] = "true"
    elif encryption_type == "ssl":
        smtp_config["ssl"] = "true"
        smtp_config["starttls"] = "false"
    else:
        smtp_config["ssl"] = "false"
        smtp_config["starttls"] = "false"

    use_auth = q.confirm(
        "Does the SMTP server require authentication?",
        default=True,
    ).unsafe_ask()
    smtp_config["auth"] = "true" if use_auth else "false"

    if use_auth:
        # We currently only support basic (password-based) authentication. Bearer token
        # authentication is not supported - there is no need for it yet in our use case.
        smtp_config["authType"] = "basic"

        smtp_config["user"] = q.text(
            "SMTP username:",
        ).unsafe_ask()

        smtp_config["password"] = q.password(
            "SMTP password:",
        ).unsafe_ask()

    smtp_config["from"] = q.text(
        "Mail address used in the 'From' header:",
        default=smtp_config["user"] if smtp_config["user"] else "noreply@vantage6.ai",
    ).unsafe_ask()

    smtp_config["fromDisplayName"] = q.text(
        "Display name used in the 'From' header (optional, press Enter to skip):",
        default="",
    ).unsafe_ask()

    smtp_config["replyTo"] = q.text(
        "Reply-to email address (optional, press Enter to skip):",
        default="",
    ).unsafe_ask()

    smtp_config["replyToDisplayName"] = q.text(
        "Reply-to display name (optional, press Enter to skip):",
        default="",
    ).unsafe_ask()

    config["keycloak"]["smtpServer"] = smtp_config

    # if we add email server, we can also enable reset password and verify email
    config["keycloak"]["resetPasswordAllowed"] = True
    config["keycloak"]["verifyEmail"] = q.confirm(
        "Do you want to require users to verify their email address?",
        default=True,
    ).unsafe_ask()

    return config


def _add_external_database_config(config: dict, k8s_node: str | None = None) -> dict:
    """
    Add external database configuration for Keycloak.

    Keycloak uses separate fields (host, database, username, password) instead of a URI.
    This function prompts for a database URI and parses it to extract the required fields.

    Parameters
    ----------
    config : dict
        The configuration dictionary
    k8s_node : str | None
        The Kubernetes node name. Used to replace localhost with appropriate hostname.

    Returns
    -------
    dict
        The configuration dictionary with external database settings added
    """
    info("For production environments, it is recommended to use an external database.")
    info("Please provide the URI of the external database.")
    info("Example: postgresql://username:password@localhost:5432/keycloak")

    database_uri = get_external_database_url(InstanceType.AUTH)

    config["database"] = parse_database_uri_to_config(database_uri, k8s_node=k8s_node)

    return config


def parse_database_uri_to_config(
    database_uri: str, k8s_node: str | None = None
) -> dict:
    """
    Parse a database URI to a configuration dictionary.

    Parameters
    ----------
    database_uri : str
        The database URI to parse
    k8s_node : str | None
        The Kubernetes node name. If provided and hostname is 'localhost',
        it will be replaced with 'host.docker.internal' for Docker Desktop
        or '172.17.0.1' for Linux.

    Returns
    -------
    dict
        Dictionary with parsed database configuration
    """
    try:
        # Replace localhost in URI if needed
        database_uri = replace_localhost_for_k8s(database_uri, k8s_node)

        parsed = urlparse(database_uri)
        username = parsed.username
        password = parsed.password
        hostname = parsed.hostname
        port = parsed.port or 5432
        database_name = parsed.path.lstrip("/") or "vantage6_auth"

        return {
            "external": True,
            "host": hostname,
            "port": port,
            "name": database_name,
            "username": username,
            "password": password,
        }

    except Exception as e:
        error(f"Failed to parse database URI: {e}")
        error(
            "Please use format: postgresql://username:password@hostname:port/database"
        )
        exit(1)


def _add_keycloak_admin_secret(
    config: dict[str, Any],
    name: str,
    k8s_cfg: KubernetesConfig,
    credentials: dict[AuthCredentials, Any],
) -> dict[str, Any]:
    """
    Add the Keycloak admin secret to the config.

    Parameters
    ----------
    config: dict[str, Any]
        The configuration for the authentication service
    name: str
        The name of the authentication service
    k8s_cfg: KubernetesConfig
        The Kubernetes configuration
    credentials: dict[AuthCredentials, Any]
        Dictionary with the credentials for the authentication service. This will be
        updated with the new credentials.

    Returns
    -------
    dict[str, Any]
        The updated configuration for the authentication service
    """
    admin_user = q.text(
        "Keycloak admin username:",
        default="admin",
    ).unsafe_ask()

    provide_password = q.confirm(
        "Do you want to provide the Keycloak admin password yourself? Choosing 'no' "
        "will store a strong password in a Kubernetes secret and print it once.",
        default=False,
    ).unsafe_ask()

    if provide_password:
        admin_password = q.password(
            "Enter Keycloak admin password (stored in a Kubernetes secret):"
        ).unsafe_ask()
    else:
        admin_password = generate_password()

    # Determine namespace/context and create a Kubernetes Secret with the credentials
    try:
        secret_name = (
            f"{APPNAME}-{name}-{InstanceType.AUTH.value}-kc-admin-user-"
            f"{uuid.uuid4().hex[:8]}"
        )
        create_kubernetes_secret(
            core_api=get_core_api_with_ssl_handling(),
            secret_name=secret_name,
            namespace=k8s_cfg.namespace,
            secret_data={"username": admin_user, "password": admin_password},
        )
    except Exception as exc:
        error(f"Failed to create Keycloak admin secret: {exc}")
        exit(1)

    credentials[AuthCredentials.KEYCLOAK_ADMIN_USER] = admin_user
    credentials[AuthCredentials.KEYCLOAK_ADMIN_PASSWORD] = admin_password

    config["keycloak"]["adminUserSecret"] = secret_name

    return config
