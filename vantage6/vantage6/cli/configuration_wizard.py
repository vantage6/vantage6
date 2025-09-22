from pathlib import Path

import questionary as q

from vantage6.common import error, info
from vantage6.common.context import AppContext
from vantage6.common.globals import (
    DEFAULT_API_PATH,
    InstanceType,
    Ports,
)

from vantage6.cli.configuration_manager import (
    AlgorithmStoreConfigurationManager,
    AuthConfigurationManager,
    NodeConfigurationManager,
    ServerConfigurationManager,
)
from vantage6.cli.context import select_context_class


def add_common_server_config(
    config: dict, instance_type: InstanceType, instance_name: str
) -> dict:
    """
    Part of the questionaire that is common to all server types (vantage6
    server and algorithm store server).

    Parameters
    ----------
    instance_type : InstanceType
        Type of server instance.
    instance_name : str
        Name of the server instance.

    Returns
    -------
    dict
        Dictionary with new (partial) server configuration
    """
    backend_config = (
        config["server"] if instance_type == InstanceType.SERVER else config["store"]
    )

    backend_config["port"] = q.text(
        "Enter port to which the server listens:",
        default=(
            str(Ports.DEV_SERVER)
            if instance_type == InstanceType.SERVER
            else str(Ports.DEV_ALGO_STORE)
        ),
    ).unsafe_ask()

    res = q.select(
        "Which level of logging would you like?",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
    ).unsafe_ask()

    backend_config["logging"] = {
        "level": res,
        "file": f"{instance_name}.log",
        "use_console": True,
        "backup_count": 5,
        "max_size": 1024,
        "format": "%(asctime)s - %(name)-14s - %(levelname)-8s - %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S",
        "loggers": [
            {"name": "urllib3", "level": "warning"},
            {"name": "socketIO-client", "level": "warning"},
            {"name": "socketio.server", "level": "warning"},
            {"name": "engineio.server", "level": "warning"},
            {"name": "sqlalchemy.engine", "level": "warning"},
        ],
    }

    backend_config["api_path"] = DEFAULT_API_PATH

    # === Database settings ===
    config["database"]["volumePath"] = q.text(
        "Where is your server database located on the host machine?",
        default=f"{Path.cwd()}/dev/.db/db_pv_server",
    ).unsafe_ask()

    config["database"]["k8sNodeName"] = q.text(
        "What is the name of the k8s node where the databases are running?",
        default="docker-desktop",
    ).unsafe_ask()

    is_production = q.confirm(
        "Do you want to use production settings for this server? If not, the server will "
        "be configured to be more suitable for development or testing purposes.",
        default=True,
    ).unsafe_ask()

    if is_production:
        config = _add_production_server_config(config)

    return config, is_production


def _add_production_server_config(config: dict) -> dict:
    """
    Add the production server configuration to the config

    Parameters
    ----------
    config : dict
        The config to add the production server configuration to

    Returns
    -------
    dict
        The config with the production server configuration added
    """
    info("For production environments, it is recommended to use an external database.")
    info("Please provide the URI of the external database.")
    info("Example: postgresql://username:password@localhost:5432/vantage6")

    config["database"]["external"] = True
    config["database"]["uri"] = q.text(
        "Database URI:",
        default="postgresql://vantage6:vantage6@localhost:5432/vantage6",
    ).unsafe_ask()

    return config


def configuration_wizard(
    questionnaire_function: callable,
    type_: InstanceType,
    instance_name: str,
    system_folders: bool,
) -> Path:
    """
    Create a configuration file for a node or server instance.

    Parameters
    ----------
    questionnaire_function : callable
        Function to generate the configuration
    type_ : InstanceType
        Type of the instance to create a configuration for
    instance_name : str
        Name of the instance
    system_folders : bool
        Whether to use the system folders or not

    Returns
    -------
    Path
        Path to the configuration file
    """
    # for defaults and where to save the config
    dirs = AppContext.instance_folders(type_, instance_name, system_folders)

    # invoke questionaire to create configuration file
    if type_ == InstanceType.NODE:
        config = questionnaire_function(dirs, instance_name)
    else:
        config = questionnaire_function(instance_name)

    # in the case of an environment we need to add it to the current
    # configuration. In the case of application we can simply overwrite this
    # key (although there might be environments present)
    config_file = Path(dirs.get("config")) / (instance_name + ".yaml")
    if type_ == InstanceType.NODE:
        conf_manager = NodeConfigurationManager
    elif type_ == InstanceType.SERVER:
        conf_manager = ServerConfigurationManager
    elif type_ == InstanceType.ALGORITHM_STORE:
        conf_manager = AlgorithmStoreConfigurationManager
    elif type_ == InstanceType.AUTH:
        conf_manager = AuthConfigurationManager
    else:
        raise ValueError(f"Invalid instance type: {type_}")

    if Path(config_file).exists():
        config_manager = conf_manager.from_file(config_file)
    else:
        config_manager = conf_manager(instance_name)

    config_manager.put(config)
    config_manager.save(config_file)

    return config_file


def select_configuration_questionaire(type_: InstanceType, system_folders: bool) -> str:
    """
    Ask which configuration the user wants to use. It shows only configurations
    that are in the default folder.

    Parameters
    ----------
    type_ : InstanceType
        Type of the instance to create a configuration for
    system_folders : bool
        Whether to use the system folders or not

    Returns
    -------
    str
        Name of the configuration
    """
    context = select_context_class(type_)
    configs, _ = context.available_configurations(system_folders)

    # each collection (file) can contain multiple configs. (e.g. test,
    # dev)
    choices = []
    for config_collection in configs:
        choices.append(
            q.Choice(title=f"{config_collection.name:25}", value=config_collection.name)
        )

    if not choices:
        raise Exception("No configurations could be found!")

    # pop the question
    try:
        return q.select(
            "Select the configuration you want to use:", choices=choices
        ).unsafe_ask()
    except KeyboardInterrupt:
        error("Aborted by user!")
        exit(1)
