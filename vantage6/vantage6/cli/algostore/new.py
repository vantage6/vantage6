import questionary as q

from vantage6.common.context import AppContext
from vantage6.common.globals import (
    InstanceType,
)

from vantage6.cli.configuration_create import add_common_backend_config


def algo_store_configuration_questionaire(
    instance_name: str, system_folders: bool
) -> dict:
    """
    Questionary to generate a config file for the algorithm store
    instance.

    Parameters
    ----------
    instance_name : str
        Name of the store instance.
    system_folders : bool
        Whether to use system folders or user folders.

    Returns
    -------
    dict
        Dictionary with the new store configuration
    """
    config = {"store": {"keycloak": {}}, "database": {}}

    config = add_common_backend_config(
        config, InstanceType.ALGORITHM_STORE, instance_name
    )

    # ask about openness of the algorithm store
    config["store"]["policies"] = {}
    is_open = q.confirm(
        "Do you want to open the algorithm store to the public? This will allow anyone "
        "to view the algorithms, but they cannot modify them.",
        default=False,
    ).unsafe_ask()
    if is_open:
        open_algos_policy = "public"
    else:
        is_open_to_whitelist = q.confirm(
            "Do you want to allow all authenticated users to access "
            "the algorithms in the store? If not allowing this, you will have to assign"
            " the appropriate permissions to each user individually.",
            default=True,
        ).unsafe_ask()
        open_algos_policy = "authenticated" if is_open_to_whitelist else "private"
    config["store"]["policies"]["algorithm_view"] = open_algos_policy

    dirs = AppContext.instance_folders(
        InstanceType.ALGORITHM_STORE, instance_name, system_folders
    )
    log_dir = str(dirs["log"])
    config["store"]["logging"]["volumeHostPath"] = log_dir

    return config
