from collections.abc import Callable
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
    HQConfigurationManager,
    NodeConfigurationManager,
)
from vantage6.cli.context import select_context_class
from vantage6.cli.utils import merge_nested_dicts


def add_common_backend_config(
    config: dict, instance_type: InstanceType, instance_name: str
) -> dict:
    """
    Part of the questionaire that is common to all backend types (HQ and algorithm
    store).

    Parameters
    ----------
    instance_type : InstanceType
        Type of backend instance.
    instance_name : str
        Name of the backend instance.

    Returns
    -------
    dict
        Dictionary with new (partial) backend configuration
    """
    service_name = "hq" if instance_type == InstanceType.HQ else "store"
    backend_config = config[service_name]

    backend_config["port"] = q.text(
        f"Enter port to which the {service_name} listens:",
        default=str(Ports.HTTPS),
    ).unsafe_ask()

    backend_config["logging"] = {
        "file": f"{instance_name}-{service_name}.log",
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

    config = add_database_config(config, instance_type)

    config = _add_production_backend_config(config)

    return config


def add_database_config(config: dict, instance_type: InstanceType) -> dict:
    """
    Add the database configuration to the config
    """
    if instance_type == InstanceType.HQ:
        service_name = "HQ"
    elif instance_type == InstanceType.ALGORITHM_STORE:
        service_name = "store"
    elif instance_type == InstanceType.AUTH:
        service_name = "auth"
    else:
        raise ValueError(f"Invalid instance type: {instance_type}")

    # === Database settings ===
    # TODO v5+ this should be updated to allow for remote databases.
    config["database"]["volumePath"] = q.text(
        f"Where is your {service_name} database located on the host machine?",
        default=f"{Path.cwd()}/dev/.db/db_pv_{service_name}",
    ).unsafe_ask()

    return config


def _add_production_backend_config(config: dict) -> dict:
    """
    Add the production backend configuration to the config

    Parameters
    ----------
    config : dict
        The config to add the production backend configuration to

    Returns
    -------
    dict
        The config with the production backend configuration added
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


def make_configuration(
    config_producing_func: Callable,
    config_producing_func_args: tuple,
    type_: InstanceType,
    instance_name: str,
    system_folders: bool,
    is_sandbox: bool = False,
    extra_config: dict | None = None,
) -> tuple[dict, Path]:
    """
    Create a configuration file for a vantage6 infrastructure component.

    Parameters
    ----------
    config_producing_func : Callable
        Function to generate the configuration
    config_producing_func_args : tuple
        Arguments to pass to the config producing function
    type_ : InstanceType
        Type of the instance to create a configuration for
    instance_name : str
        Name of the instance
    system_folders : bool
        Whether to use the system folders or not
    is_sandbox : bool
        Whether to create a sandbox configuration or not
    extra_config: dict | None = None
        Extra configuration to add. Note that this may overwrite the configuration
        produced by the config producing function if the keys overlap.

    Returns
    -------
    tuple[dict, Path]
        Dictionary with the configuration and path to the configuration file
    """
    # for defaults and where to save the config
    dirs = AppContext.instance_folders(type_, instance_name, system_folders)

    # invoke function to create configuration file. Usually this is a questionaire
    # but it can also be a function that immediately returns a dict with the
    # configuration.
    config: dict = config_producing_func(*config_producing_func_args)

    if extra_config:
        config = merge_nested_dicts(config, extra_config)

    # in the case of an environment we need to add it to the current
    # configuration. In the case of application we can simply overwrite this
    # key (although there might be environments present)
    config_file = Path(dirs.get("config")) / (instance_name + ".yaml")
    if type_ == InstanceType.NODE:
        conf_manager = NodeConfigurationManager
    elif type_ == InstanceType.HQ:
        conf_manager = HQConfigurationManager
    elif type_ == InstanceType.ALGORITHM_STORE:
        conf_manager = AlgorithmStoreConfigurationManager
    elif type_ == InstanceType.AUTH:
        conf_manager = AuthConfigurationManager
    else:
        raise ValueError(f"Invalid instance type: {type_}")

    if Path(config_file).exists():
        config_manager = conf_manager.from_file(config_file, is_sandbox=is_sandbox)
    else:
        config_manager = conf_manager(instance_name, is_sandbox=is_sandbox)

    config_manager.put(config)
    config_file = config_manager.save(config_file)

    return config, config_file


def select_configuration_questionnaire(
    type_: InstanceType, system_folders: bool, is_sandbox: bool = False
) -> str:
    """
    Ask which configuration the user wants to use. It shows only configurations
    that are in the default folder.

    Parameters
    ----------
    type_ : InstanceType
        Type of the instance to create a configuration for
    system_folders : bool
        Whether to use the system folders or not
    is_sandbox : bool
        Whether to show only the sandbox configurations or not

    Returns
    -------
    str
        Name of the configuration
    """
    context = select_context_class(type_)
    configs, _ = context.available_configurations(system_folders, is_sandbox)

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
