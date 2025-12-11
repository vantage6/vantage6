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
