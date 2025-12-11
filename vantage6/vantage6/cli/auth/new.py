import uuid
from typing import Any

import click
import questionary as q

from vantage6.common import error, info
from vantage6.common.globals import (
    InstanceType,
)

from vantage6.cli.common.new import new
from vantage6.cli.common.utils import create_kubernetes_secret, generate_password
from vantage6.cli.configuration_create import add_database_config
from vantage6.cli.globals import APPNAME, DEFAULT_SERVER_SYSTEM_FOLDERS
from vantage6.cli.k8s_config import KubernetesConfig, select_k8s_config
from vantage6.cli.utils import prompt_config_name
from vantage6.cli.utils_kubernetes import get_core_api_with_ssl_handling

# Store credentials generated during the setup process in a global, so that they can
# be printed at the end of the setup process.
CREDENTIALS = {}


@click.command()
@click.option(
    "-n", "--name", default=None, help="name of the configuration you want to use."
)
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Use system folders instead of user folders. This is the default",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=DEFAULT_SERVER_SYSTEM_FOLDERS,
    help="Use user folders instead of system folders",
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
def cli_auth_new(
    name: str,
    system_folders: bool,
    context: str | None,
    namespace: str | None,
) -> None:
    """
    Create a new server configuration.
    """
    name = prompt_config_name(name)
    k8s_cfg = select_k8s_config(context=context, namespace=namespace)
    new(
        config_producing_func=auth_configuration_questionaire,
        config_producing_func_args=(name, k8s_cfg),
        name=name,
        system_folders=system_folders,
        type_=InstanceType.AUTH,
    )
    if CREDENTIALS:
        _print_credentials_one_time()


def auth_configuration_questionaire(
    name: str, k8s_cfg: KubernetesConfig
) -> dict[str, Any]:
    """
    Kubernetes-specific questionnaire to generate Helm values for the Keycloak helm
    chart.

    Parameters
    ----------
    name: str
        The name of the authentication service
    k8s_cfg: KubernetesConfig
        The Kubernetes configuration

    Returns
    -------
    dict[str, Any]
        The configuration for the authentication service
    """
    config = {"keycloak": {}, "database": {}}

    is_production = q.confirm(
        "Do you want to use production settings? If not, the service will be configured"
        " to be more suitable for development or testing purposes.",
        default=True,
    ).unsafe_ask()

    config["keycloak"]["production"] = is_production

    config = add_database_config(config, InstanceType.AUTH)

    config = _add_keycloak_admin_secret(config, name, k8s_cfg)
    if is_production:
        config = _add_keycloak_admin_secret(config, name, k8s_cfg)

        ui_url = q.text(
            "Please provide the URL of the UI. This is the URL that users will use to "
            "log in to the service.",
            default="https://ui.vantage6.ai",
        ).unsafe_ask()
        # add http://localhost:7681 as that is used by the Python client
        config["keycloak"]["redirectUris"] = [ui_url, "http://localhost:7681"]

    return config


def _add_keycloak_admin_secret(
    config: dict[str, Any], name: str, k8s_cfg: KubernetesConfig
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
        "Do you want to provide the Keycloak admin password yourself? "
        "Choosing 'no' will generate a strong password and print it once.",
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

    CREDENTIALS["keycloakAdminUser"] = admin_user
    CREDENTIALS["keycloakAdminPassword"] = admin_password

    config["keycloak"]["adminUserSecret"] = secret_name

    return config


def _print_credentials_one_time() -> None:
    """
    Print the used credentials one time.
    """
    info("--------------------------------")
    info(
        "In setting up the service, you generated credentials that have been stored"
        " in Kubernetes secrets."
    )
    info(
        "Do NOT delete the Kubernetes secrets as long as you use this authentication "
        "service."
    )
    info("This is a one-time print of the credentials. They will not be printed again.")
    info("--------------------------------")
    if "keycloakAdminUser" in CREDENTIALS:
        info(f"Keycloak admin username: {CREDENTIALS['keycloakAdminUser']}")
    if "keycloakAdminPassword" in CREDENTIALS:
        info(f"Keycloak admin password: {CREDENTIALS['keycloakAdminPassword']}")
    info("--------------------------------")
