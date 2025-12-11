from typing import Any

import click
import questionary as q

from vantage6.common.context import AppContext
from vantage6.common.globals import (
    InstanceType,
)

from vantage6.cli.configuration_create import add_common_server_config
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS
from vantage6.cli.k8s_config import KubernetesConfig


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


def server_configuration_questionaire(
    instance_name: str, system_folders: bool, k8s_config: KubernetesConfig
) -> dict[str, Any]:
    """
    Kubernetes-specific questionnaire to generate Helm values for server.

    Parameters
    ----------
    instance_name : str
        Name of the server instance.
    system_folders : bool
        Whether to use system folders or user folders.
    k8s_cfg : KubernetesConfig
        Kubernetes configuration.

    Returns
    -------
    dict[str, Any]
        dictionary with Helm values for the server configuration
    """
    dirs = AppContext.instance_folders(
        InstanceType.SERVER, instance_name, system_folders
    )
    log_dir = dirs.get("log")

    # Initialize config with basic structure
    config = {"server": {}, "database": {}, "ui": {}, "rabbitmq": {}, "prometheus": {}}

    config = add_common_server_config(config, InstanceType.SERVER, instance_name)

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

    # set directory to store log files on host machine
    config["server"]["logging"]["volumeHostPath"] = str(log_dir)

    return config
