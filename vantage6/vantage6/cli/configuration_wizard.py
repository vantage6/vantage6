import questionary as q

from pathlib import Path

from vantage6.common import generate_apikey
from vantage6.common.globals import DATABASE_TYPES
from vantage6.common.client.node_client import NodeClient
from vantage6.common import error, warning
from vantage6.cli.context import NodeContext, ServerContext
from vantage6.cli.configuration_manager import (
    NodeConfigurationManager,
    ServerConfigurationManager
)


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
    config = q.prompt([
        {
            "type": "text",
            "name": "api_key",
            "message": "Enter given api-key:"
        },
        {
            "type": "text",
            "name": "server_url",
            "message": "The base-URL of the server:",
            "default": "http://localhost"
        },
        {
            "type": "text",
            "name": "port",
            "message": "Enter port to which the server listens:",
            "default": "5000"
        },
        {
            "type": "text",
            "name": "api_path",
            "message": "Path of the api:",
            "default": "/api"
        },
        {
            "type": "text",
            "name": "task_dir",
            "message": "Task directory path:",
            "default": str(dirs["data"])
        }
    ])

    config["databases"] = list()
    while q.confirm("Do you want to add a database?").ask():
        db_label = q.prompt([
            {
                "type": "text",
                "name": "label",
                "message": "Enter unique label for the database:",
                "default": "default"
            }
        ])
        db_path = q.prompt([
            {
                "type": "text",
                "name": "uri",
                "message": "Database URI:"
            }
        ])
        db_type = q.select("Database type:", choices=DATABASE_TYPES).ask()

        config["databases"].append(
            {
                "label": db_label.get("label"),
                "uri": db_path.get("uri"),
                "type": db_type
            }
        )

    res = q.select("Which level of logging would you like?",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL",
                            "NOTSET"]).ask()

    is_add_vpn = q.confirm(
        "Do you want to connect to a VPN server?", default=False).ask()
    if is_add_vpn:
        config['vpn_subnet'] = q.text(
            message="Subnet of the VPN server you want to connect to:",
            default='10.76.0.0/16'
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
        ]
    }

    # Check if we can login to the server to retrieve collaboration settings
    client = NodeClient(config['server_url'], config['port'],
                        config['api_path'])
    try:
        client.authenticate(config['api_key'])
    except Exception as e:
        error(f"Could not authenticate with server: {e}")
        error("Please check (1) your API key and (2) if your server is online")
        warning("If you continue, you should provide your collaboration "
                "settings manually.")
        if q.confirm("Do you want to abort?", default=True).ask():
            exit(0)

    if client.whoami is not None:
        encryption = client.is_encrypted_collaboration()
        # TODO when we build collaboration policies, update this to provide
        # the node admin with a list of all policies, and whether or not
        # to accept them
        q.confirm(f"Encryption is {'enabled' if encryption else 'disabled'}"
                  f" for this collaboration. Accept?", default=True).ask()
    else:
        encryption = q.confirm("Enable encryption?", default=True).ask()

    private_key = "" if not encryption else \
        q.text("Path to private key file:").ask()

    config["encryption"] = {
        "enabled": encryption == "true",
        "private_key": private_key
    }

    return config


def server_configuration_questionaire(instance_name: str) -> dict:
    """
    Questionary to generate a config file for the node instance.

    Parameters
    ----------
    instance_name : str
        Name of the node instance.

    Returns
    -------
    dict
        Dictionary with the new server configuration
    """

    config = q.prompt([
        {
            "type": "text",
            "name": "description",
            "message": "Enter a human-readable description:"
        },
        {
            "type": "text",
            "name": "ip",
            "message": "ip:",
            "default": "0.0.0.0"
        },
        {
            "type": "text",
            "name": "port",
            "message": "Enter port to which the server listens:",
            "default": "5000"
        },
        {
            "type": "text",
            "name": "api_path",
            "message": "Path of the api:",
            "default": "/api"
        },
        {
            "type": "text",
            "name": "uri",
            "message": "Database URI:",
            "default": "sqlite:///default.sqlite"
        },
        {
            "type": "select",
            "name": "allow_drop_all",
            "message": "Allowed to drop all tables: ",
            "choices": ["True", "False"]
        }
    ])

    constant_jwt_secret = q.confirm("Do you want a constant JWT secret?").ask()
    if constant_jwt_secret:
        config["jwt_secret_key"] = generate_apikey()

    res = q.select("Which level of logging would you like?",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR",
                            "CRITICAL", "NOTSET"]).ask()

    is_mfa = q.confirm(
        "Do you want to enforce two-factor authentication?"
    ).ask()
    if is_mfa:
        config['two_factor_auth'] = is_mfa

    is_add_vpn = q.confirm(
        "Do you want to add a VPN server?", default=False).ask()
    if is_add_vpn:
        vpn_config = q.prompt([
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
                "default": "http://localhost"
            }
        ])
        config['vpn_server'] = vpn_config

    is_add_rabbitmq = q.confirm(
        "Do you want to add a RabbitMQ message queue?").ask()
    if is_add_rabbitmq:
        rabbit_uri = q.text(
            message='Enter the URI for your RabbitMQ:'
        ).ask()
        run_rabbit_locally = q.confirm(
            "Do you want to run RabbitMQ locally? (Use only for testing)"
        ).ask()
        config['rabbitmq'] = {
            'uri': rabbit_uri,
            'start_with_server': run_rabbit_locally
        }

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
        ]
    }

    return config


def configuration_wizard(type_: str, instance_name: str,
                         system_folders: bool) -> Path:
    """
    Create a configuration file for a node or server instance.

    Parameters
    ----------
    type_ : str
        Type of the instance. Either "node" or "server"
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
    dirs = NodeContext.instance_folders(type_, instance_name, system_folders)

    # invoke questionaire to create configuration file
    if type_ == "node":
        conf_manager = NodeConfigurationManager
        config = node_configuration_questionaire(dirs, instance_name)
    else:
        conf_manager = ServerConfigurationManager
        config = server_configuration_questionaire(instance_name)

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


def select_configuration_questionaire(type_: str, system_folders: bool) -> str:
    """
    Ask which configuration the user wants to use. It shows only configurations
    that are in the default folder.

    Parameters
    ----------
    type_ : str
        Type of the instance. Either "node" or "server"
    system_folders : bool
        Whether to use the system folders or not

    Returns
    -------
    str
        Name of the configuration
    """
    context = NodeContext if type_ == "node" else ServerContext
    configs, _ = context.available_configurations(system_folders)

    # each collection (file) can contain multiple configs. (e.g. test,
    # dev)
    choices = []
    for config_collection in configs:
        choices.append(q.Choice(
            title=f"{config_collection.name:25}",
            value=config_collection.name
        ))

    if not choices:
        raise Exception("No configurations could be found!")

    # pop the question
    return q.select("Select the configuration you want to use:",
                    choices=choices).ask()
