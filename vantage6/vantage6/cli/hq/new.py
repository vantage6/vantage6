from typing import Any

import questionary as q

from vantage6.common.context import AppContext
from vantage6.common.globals import (
    MAIN_VERSION_NAME,
    InstanceType,
)

from vantage6.cli.auth.new import generate_password
from vantage6.cli.configuration_create import add_common_backend_config


def hq_configuration_questionaire(
    instance_name: str, system_folders: bool
) -> dict[str, Any]:
    """
    Kubernetes-specific questionnaire to generate Helm values for HQ.

    Parameters
    ----------
    instance_name : str
        Name of the HQ instance.
    system_folders : bool
        Whether to use system folders or user folders.

    Returns
    -------
    dict[str, Any]
        dictionary with Helm values for the HQ configuration
    """
    dirs = AppContext.instance_folders(InstanceType.HQ, instance_name, system_folders)
    log_dir = dirs.get("log")

    # Initialize config with basic structure
    config = {
        "hq": {"keycloak": {}},
        "database": {},
        "ui": {},
        "rabbitmq": {},
        "prometheus": {},
    }

    config = add_common_backend_config(config, InstanceType.HQ, instance_name)

    # TODO v5+ these should be removed, latest should usually be used so question is
    # not needed. However, for now we want to specify alpha/beta images.
    # === HQ settings ===
    config["hq"]["image"] = q.text(
        "HQ Docker image:",
        default=f"harbor2.vantage6.ai/infrastructure/hq:{MAIN_VERSION_NAME}",
    ).unsafe_ask()

    # === UI settings ===
    config["ui"]["image"] = q.text(
        "UI Docker image:",
        default=f"harbor2.vantage6.ai/infrastructure/ui:{MAIN_VERSION_NAME}",
    ).unsafe_ask()

    # TODO v5+ we need to add a question to ask which algorithm stores are allowed, to
    # set the CSP headers in the UI. This is not done now because it becomes easier when
    # store and keycloak service can also be setup in the `v6 hq new` command.

    # set directory to store log files on host machine
    config["hq"]["logging"]["volumeHostPath"] = str(log_dir)

    # set strong password for RabbitMQ
    config["rabbitmq"]["password"] = generate_password()

    return config
