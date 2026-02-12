from typing import Any

import questionary as q

from vantage6.common import info
from vantage6.common.context import AppContext
from vantage6.common.globals import (
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

    config = _set_allowed_algorithm_stores(config)

    # set directory to store log files on host machine
    config["hq"]["logging"]["volumeHostPath"] = str(log_dir)

    # set strong password for RabbitMQ
    config["rabbitmq"]["password"] = generate_password()

    return config


def _set_allowed_algorithm_stores(config: dict) -> dict:
    """
    Prompt the user for the allowed algorithm stores on their HQ.

    Parameters
    ----------
    config : dict
        Configuration dictionary.

    Returns
    -------
    dict
        Configuration dictionary with allowed algorithm stores.
    """
    info(
        "As security setting in the UI, we only allow traffic from certain external "
        "domains. These are vantage6 HQ and relevant algorithm stores."
    )
    info("Limiting the allowed algorithm stores is recommended.")
    setup_allowed_stores = q.confirm(
        "In the UI, do you want to only allow algorithms from specific algorithm "
        "stores? ",
        default=True,
    ).unsafe_ask()
    if setup_allowed_stores:
        config["ui"]["allowedAlgorithmStores"] = q.text(
            "Enter the URLs of all the algorithm stores you want to allow "
            "(comma-separated). Use * to allow all stores (less secure):",
            default="https://store.uluru.vantage6.ai",
        ).unsafe_ask()
    return config
