import questionary as q

from pathlib import Path

from vantage6.common import generate_apikey
from vantage6.common.globals import DATABASE_TYPES, InstanceType
from vantage6.common.client.node_client import NodeClient
from vantage6.common.context import AppContext
from vantage6.common import error, warning
from vantage6.cli.context import select_context_class
from vantage6.cli.configuration_manager import (
    NodeConfigurationManager,
    ServerConfigurationManager,
)
from vantage6.cli.globals import AlgoStoreGlobals, ServerGlobals


def node_configuration_questionaire(dirs: dict, instance_name: str) -> dict:
    """
    Questionary to generate a config file for the node instance.

    Parameters
    ----------
    dirs : dict
        Dictionary with the directories of the node instance.
    instance_name : str
        Name of the node instance.

    Returns
    -------
    dict
        Dictionary with the new node configuration
    """
    config = q.prompt(
        [
            {"type": "text", "name": "api_key", "message": "Enter given api-key:"},
            {
                "type": "text",
                "name": "server_url",
                "message": "The base-URL of the server:",
                "default": "http://localhost",
            },
            {
                "type": "text",
                "name": "port",
                "message": "Enter port to which the server listens:",
                "default": "5000",
            },
            {
                "type": "text",
                "name": "api_path",
                "message": "Path of the api:",
                "default": "/api",
            },
            {
                "type": "text",
                "name": "task_dir",
                "message": "Task directory path:",
                "default": str(dirs["data"]),
            },
        ]
    )

    config["databases"] = list()
    while q.confirm("Do you want to add a database?").ask():
        db_label = q.prompt(
            [
                {
                    "type": "text",
                    "name": "label",
                    "message": "Enter unique label for the database:",
                    "default": "default",
                }
            ]
        )
        db_path = q.prompt(
            [{"type": "text", "name": "uri", "message": "Database URI:"}]
        )
        db_type = q.select("Database type:", choices=DATABASE_TYPES).ask()

        config["databases"].append(
            {"label": db_label.get("label"), "uri": db_path.get("uri"), "type": db_type}
        )

    res = q.select(
        "Which level of logging would you like?",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"],
    ).ask()

    is_add_vpn = q.confirm(
        "Do you want to connect to a VPN server?", default=False
    ).ask()
    if is_add_vpn:
        config["vpn_subnet"] = q.text(
            message="Subnet of the VPN server you want to connect to:",
            default="10.76.0.0/16",
        ).ask()

    config["logging"] = {
        "level": res,
        "use_console": True,
        "backup_count": 5,
        "max_size": 1024,
        "format": "%(asctime)s - %(name)-14s - %(levelname)-8s - %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S",
        "loggers": [
            {"name": "urllib3", "level": "warning"},
            {"name": "requests", "level": "warning"},
            {"name": "engineio.client", "level": "warning"},
            {"name": "docker.utils.config", "level": "warning"},
            {"name": "docker.auth", "level": "warning"},
        ],
    }

    # Check if we can login to the server to retrieve collaboration settings
    client = NodeClient(config["server_url"], config["port"], config["api_path"])
    try:
        client.authenticate(config["api_key"])
    except Exception as e:
        error(f"Could not authenticate with server: {e}")
        error("Please check (1) your API key and (2) if your server is online")
        warning(
            "If you continue, you should provide your collaboration "
            "settings manually."
        )
        if q.confirm("Do you want to abort?", default=True).ask():
            exit(0)

    if client.whoami is not None:
        encryption = client.is_encrypted_collaboration()
        # TODO when we build collaboration policies, update this to provide
        # the node admin with a list of all policies, and whether or not
        # to accept them
        q.confirm(
            f"Encryption is {'enabled' if encryption else 'disabled'}"
            f" for this collaboration. Accept?",
            default=True,
        ).ask()
    else:
        encryption = q.confirm("Enable encryption?", default=True).ask()

    private_key = "" if not encryption else q.text("Path to private key file:").ask()

    config["encryption"] = {
        "enabled": encryption is True or encryption == "true",
        "private_key": private_key,
    }

    return config


def _get_common_server_config(
    instance_type: InstanceType, instance_name: str, include_api_path: bool = True
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
    include_api_path : bool
        Whether to include the api path in the questionaire.

    Returns
    -------
    dict
        Dictionary with new (partial) server configuration
    """
    config = q.prompt(
        [
            {
                "type": "text",
                "name": "description",
                "message": "Enter a human-readable description:",
            },
            {"type": "text", "name": "ip", "message": "ip:", "default": "0.0.0.0"},
            {
                "type": "text",
                "name": "port",
                "message": "Enter port to which the server listens:",
                "default": (
                    # Note that .value is required in YAML to get proper str value
                    ServerGlobals.PORT.value
                    if instance_type == InstanceType.SERVER
                    else AlgoStoreGlobals.PORT.value
                ),
            },
        ]
    )

    # TODO v5+ remove api_path. It complicates configuration
    if include_api_path:
        config.update(
            q.prompt(
                [
                    {
                        "type": "text",
                        "name": "api_path",
                        "message": "Path of the api:",
                        "default": "/api",
                    }
                ]
            )
        )

    config.update(
        q.prompt(
            [
                {
                    "type": "text",
                    "name": "uri",
                    "message": "Database URI:",
                    "default": "sqlite:///default.sqlite",
                },
                {
                    "type": "select",
                    "name": "allow_drop_all",
                    "message": "Allowed to drop all tables: ",
                    "choices": ["True", "False"],
                },
            ]
        )
    )

    res = q.select(
        "Which level of logging would you like?",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"],
    ).ask()

    config["logging"] = {
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
            {"name": "requests_oauthlib.oauth2_session", "level": "warning"},
        ],
    }

    return config


def server_configuration_questionaire(instance_name: str) -> dict:
    """
    Questionary to generate a config file for the server instance.

    Parameters
    ----------
    instance_name : str
        Name of the server instance.

    Returns
    -------
    dict
        Dictionary with the new server configuration
    """

    config = _get_common_server_config(
        InstanceType.SERVER, instance_name, include_api_path=True
    )

    constant_jwt_secret = q.confirm("Do you want a constant JWT secret?").ask()
    if constant_jwt_secret:
        config["jwt_secret_key"] = generate_apikey()

    is_mfa = q.confirm("Do you want to enforce two-factor authentication?").ask()
    if is_mfa:
        config["two_factor_auth"] = is_mfa

    current_server_url = f"http://localhost:{config['port']}{config['api_path']}"
    config["server_url"] = q.text(
        "What is the server url exposed to the users? If you are running a"
        " development server running locally, this is the same as the "
        "server url. If you are running a production server, this is the "
        "url that users will connect to.",
        default=current_server_url,
    ).ask()

    is_add_vpn = q.confirm("Do you want to add a VPN server?", default=False).ask()
    if is_add_vpn:
        vpn_config = q.prompt(
            [
                {
                    "type": "text",
                    "name": "url",
                    "message": "VPN server URL:",
                },
                {
                    "type": "text",
                    "name": "portal_username",
                    "message": "VPN portal username:",
                },
                {
                    "type": "password",
                    "name": "portal_userpass",
                    "message": "VPN portal password:",
                },
                {
                    "type": "text",
                    "name": "client_id",
                    "message": "VPN client username:",
                },
                {
                    "type": "password",
                    "name": "client_secret",
                    "message": "VPN client password:",
                },
                {
                    "type": "text",
                    "name": "redirect_url",
                    "message": "Redirect url (should be local address of server)",
                    "default": "http://localhost",
                },
            ]
        )
        config["vpn_server"] = vpn_config

    is_add_rabbitmq = q.confirm("Do you want to add a RabbitMQ message queue?").ask()
    if is_add_rabbitmq:
        rabbit_uri = q.text(message="Enter the URI for your RabbitMQ:").ask()
        run_rabbit_locally = q.confirm(
            "Do you want to run RabbitMQ locally? (Use only for testing)"
        ).ask()
        config["rabbitmq"] = {
            "uri": rabbit_uri,
            "start_with_server": run_rabbit_locally,
        }

    return config


def algo_store_configuration_questionaire(instance_name: str) -> dict:
    """
    Questionary to generate a config file for the algorithm store server
    instance.

    Parameters
    ----------
    instance_name : str
        Name of the server instance.

    Returns
    -------
    dict
        Dictionary with the new server configuration
    """
    config = _get_common_server_config(
        InstanceType.ALGORITHM_STORE, instance_name, include_api_path=False
    )
    return config


def configuration_wizard(
    type_: InstanceType, instance_name: str, system_folders: bool
) -> Path:
    """
    Create a configuration file for a node or server instance.

    Parameters
    ----------
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
        conf_manager = NodeConfigurationManager
        config = node_configuration_questionaire(dirs, instance_name)
    elif type_ == InstanceType.SERVER:
        conf_manager = ServerConfigurationManager
        config = server_configuration_questionaire(instance_name)
    else:
        conf_manager = ServerConfigurationManager
        config = algo_store_configuration_questionaire(instance_name)

    # in the case of an environment we need to add it to the current
    # configuration. In the case of application we can simply overwrite this
    # key (although there might be environments present)
    config_file = Path(dirs.get("config")) / (instance_name + ".yaml")

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
    return q.select("Select the configuration you want to use:", choices=choices).ask()
