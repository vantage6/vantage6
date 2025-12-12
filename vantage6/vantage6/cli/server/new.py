from typing import Any

import questionary as q

from vantage6.common.context import AppContext
from vantage6.common.globals import (
    MAIN_VERSION_NAME,
    InstanceType,
)

from vantage6.cli.configuration_create import add_common_server_config


def server_configuration_questionaire(
    instance_name: str, system_folders: bool
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
    config = {
        "server": {"keycloak": {}},
        "database": {},
        "ui": {},
        "rabbitmq": {},
        "prometheus": {},
    }

    config = add_common_server_config(config, InstanceType.SERVER, instance_name)

    # TODO v5+ these should be removed, latest should usually be used so question is
    # not needed. However, for now we want to specify alpha/beta images.
    # === Server settings ===
    config["server"]["image"] = q.text(
        "Server Docker image:",
        default=f"harbor2.vantage6.ai/infrastructure/server:{MAIN_VERSION_NAME}",
    ).unsafe_ask()

    # === UI settings ===
    config["ui"]["image"] = q.text(
        "UI Docker image:",
        default=f"harbor2.vantage6.ai/infrastructure/ui:{MAIN_VERSION_NAME}",
    ).unsafe_ask()

    # TODO v5+ we need to add a question to ask which algorithm stores are allowed, to
    # set the CSP headers in the UI. This is not done now because it becomes easier when
    # store and keycloak service can also be setup in the `v6 server new` command.

    # === Keycloak settings ===

    # set directory to store log files on host machine
    config["server"]["logging"]["volumeHostPath"] = str(log_dir)

    return config
