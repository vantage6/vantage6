import uuid
from typing import Any

import questionary as q

from vantage6.common import error
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import create_kubernetes_secret, generate_password
from vantage6.cli.configuration_create import add_database_config
from vantage6.cli.globals import APPNAME
from vantage6.cli.hub.utils.enum import AuthCredentials
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.utils_kubernetes import get_core_api_with_ssl_handling


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

    config = add_database_config(config, InstanceType.AUTH)

    config = _add_keycloak_admin_secret(config, name, k8s_cfg, credentials)

    config["keycloak"]["adminClientSecret"] = _get_admin_client_secret()

    config["keycloak"]["adminPassword"] = _get_admin_password()

    # Add SMTP configuration if requested
    smtp_config = _get_smtp_config()
    if smtp_config:
        config["keycloak"]["smtpServer"] = smtp_config

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


def _get_smtp_config() -> dict[str, Any] | None:
    """
    Get SMTP server configuration from user.

    Returns
    -------
    dict[str, Any] | None
        Dictionary with SMTP configuration, or None if user doesn't want to configure
        SMTP
    """
    configure_smtp = q.confirm(
        "Do you want to configure an SMTP server for email sending?",
        default=False,
    ).unsafe_ask()

    if not configure_smtp:
        return None

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

    return smtp_config


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
