from typing import Any

import click
import questionary as q

from vantage6.common.globals import (
    InstanceType,
)

from vantage6.cli.common.new import new
from vantage6.cli.config import CliConfig
from vantage6.cli.configuration_wizard import add_common_server_config
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS


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
@click.option(
    "--namespace",
    default=None,
    help="Kubernetes namespace to use",
)
def cli_server_new(
    name: str,
    system_folders: bool,
    namespace: str,
    context: str,
) -> None:
    """
    Create a new server configuration.
    """
    # info(
    #     "Vantage6 uses keycloak for authentication. Please configure a keycloak "
    #     "server here unless you have one running externally."
    # )
    # configure_keycloak = q.confirm(
    #     "Do you want to configure a keycloak server?",
    #     default=True,
    # ).unsafe_ask()
    # if configure_keycloak:
    #     print("awefawef")

    new(
        questionnaire_function=server_configuration_questionaire,
        name=name,
        system_folders=system_folders,
        namespace=namespace,
        context=context,
        type_=InstanceType.SERVER,
    )


def server_configuration_questionaire(instance_name: str) -> dict[str, Any]:
    """
    Kubernetes-specific questionnaire to generate Helm values for server.

    Parameters
    ----------
    instance_name : str
        Name of the server instance.

    Returns
    -------
    dict[str, Any]
        dictionary with Helm values for the server configuration
    """
    # Initialize config with basic structure
    config = {"server": {}, "database": {}, "ui": {}, "rabbitmq": {}}

    config, is_production = add_common_server_config(
        config, InstanceType.SERVER, instance_name
    )
    if not is_production:
        config["server"]["jwt"] = {
            "secret": "constant_development_secret`",
        }
        config["server"]["dev"] = {
            "host_uri": "host.docker.internal",
            "store_in_local_cluster": True,
        }

    # TODO v5+ these should be removed, latest should usually be used so question is
    # not needed. However, for now we want to specify alpha/beta images.
    # === Server settings ===
    config["server"]["image"] = q.text(
        "Server Docker image:",
        default="harbor2.vantage6.ai/infrastructure/server:latest",
    ).unsafe_ask()

    # === UI settings ===
    config["ui"]["image"] = q.text(
        "UI Docker image:",
        default="harbor2.vantage6.ai/infrastructure/ui:latest",
    ).unsafe_ask()

    # TODO v5+ we need to add a question to ask which algorithm stores are allowed, to
    # set the CSP headers in the UI. This is not done now because it becomes easier when
    # store and keycloak service can also be setup in the `v6 server new` command.

    # === Keycloak settings ===
    cli_config = CliConfig()
    kube_namespace = cli_config.get_last_namespace()
    keycloak_url = f"http://vantage6-auth-keycloak.{kube_namespace}.svc.cluster.local"
    config["server"]["keycloakUrl"] = keycloak_url

    return config
