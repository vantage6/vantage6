from pathlib import Path

import questionary as q

from vantage6.common import generate_apikey
from vantage6.common.globals import (
    DATABASE_TYPES,
    InstanceType,
    NodePolicy,
    Ports,
    DEFAULT_API_PATH,
)
from vantage6.common.client.node_client import NodeClient
from vantage6.common.context import AppContext
from vantage6.common import error, warning, info
from vantage6.cli.context import select_context_class
from vantage6.cli.configuration_manager import (
    NodeConfigurationManager,
    ServerConfigurationManager,
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
    config = q.unsafe_prompt(
        [
            {"type": "text", "name": "api_key", "message": "Enter given api-key:"},
            {
                "type": "text",
                "name": "server_url",
                "message": "The base-URL of the server:",
                "default": "http://localhost",
            },
        ]
    )
    # remove trailing slash from server_url if entered by user
    config["server_url"] = config["server_url"].rstrip("/")

    # set default port to the https port if server_url is https
    default_port = (
        str(Ports.HTTPS.value)
        if config["server_url"].startswith("https")
        else str(Ports.DEV_SERVER.value)
    )

    config = config | q.unsafe_prompt(
        [
            {
                "type": "text",
                "name": "port",
                "message": "Enter port to which the server listens:",
                "default": default_port,
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
    while q.confirm("Do you want to add a database?").unsafe_ask():
        db_label = q.unsafe_prompt(
            [
                {
                    "type": "text",
                    "name": "label",
                    "message": "Enter unique label for the database:",
                    "default": "default",
                }
            ]
        )
        db_path = q.unsafe_prompt(
            [{"type": "text", "name": "uri", "message": "Database URI:"}]
        )
        db_type = q.select("Database type:", choices=DATABASE_TYPES).unsafe_ask()

        config["databases"].append(
            {"label": db_label.get("label"), "uri": db_path.get("uri"), "type": db_type}
        )

    is_add_vpn = q.confirm(
        "Do you want to connect to a VPN server?", default=False
    ).unsafe_ask()
    if is_add_vpn:
        config["vpn_subnet"] = q.text(
            message="Subnet of the VPN server you want to connect to:",
            default="10.76.0.0/16",
        ).unsafe_ask()

    is_policies = q.confirm(
        "Do you want to limit the algorithms allowed to run on your node? This "
        "should always be done for production scenarios.",
        default=True,
    ).unsafe_ask()
    policies = {}
    if is_policies:
        info(
            "You can limit the algorithms that can run on your node in two ways: by "
            "allowing specific algorithms or by allowing all algorithms in a given "
            "algorithm store."
        )
        ask_single_algorithms = q.confirm(
            "Do you want to enter a list of allowed algorithms?"
        ).unsafe_ask()
        if ask_single_algorithms:
            policies[NodePolicy.ALLOWED_ALGORITHMS.value] = _get_allowed_algorithms()
        ask_algorithm_stores = q.confirm(
            "Do you want to allow algorithms from specific algorithm stores?"
        ).unsafe_ask()
        if ask_algorithm_stores:
            policies[NodePolicy.ALLOWED_ALGORITHM_STORES.value] = (
                _get_allowed_algorithm_stores()
            )
        if ask_single_algorithms and ask_algorithm_stores:
            require_both_whitelists = q.confirm(
                "Do you want to allow only algorithms that are both in the list of "
                "allowed algorithms *AND* are part of one of the allowed algorithm "
                "stores? If not, algorithms will be allowed if they are in either the "
                "list of allowed algorithms or one of the allowed algorithm stores.",
                default=True,
            ).unsafe_ask()
            policies["allow_either_whitelist_or_store"] = not require_both_whitelists
    if policies:
        config["policies"] = policies

    res = q.select(
        "Which level of logging would you like?",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"],
    ).unsafe_ask()

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
        if q.confirm("Do you want to abort?", default=True).unsafe_ask():
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
        ).unsafe_ask()
    else:
        encryption = q.confirm("Enable encryption?", default=True).unsafe_ask()

    private_key = (
        "" if not encryption else q.text("Path to private key file:").unsafe_ask()
    )

    config["encryption"] = {
        "enabled": encryption is True or encryption == "true",
        "private_key": private_key,
    }

    return config


def _get_allowed_algorithms() -> list[str]:
    """
    Prompt the user for the allowed algorithms on their node

    Returns
    -------
    list[str]
        List of allowed algorithms or regular expressions to match them
    """
    info("Below you can add algorithms that are allowed to run on your node.")
    info(
        "You can use regular expressions to match multiple algorithms, or you can "
        "use strings to provide one algorithm at a time."
    )
    info("Examples:")
    info(r"^harbor2\.vantage6\.ai/demo/average$    Allow the demo average algorithm")
    info(
        r"^harbor2\.vantage6\.ai/algorithms/.*   Allow all algorithms from "
        "harbor2.vantage6.ai/algorithms"
    )
    info(
        r"^harbor2\.vantage6\.ai/demo/average@sha256:82becede...$    Allow a "
        "specific hash of average algorithm"
    )
    allowed_algorithms = []
    while True:
        algo = q.text(message="Enter your algorithm expression:").unsafe_ask()
        allowed_algorithms.append(algo)
        if not q.confirm(
            "Do you want to add another algorithm expression?", default=True
        ).unsafe_ask():
            break
    return allowed_algorithms


def _get_allowed_algorithm_stores() -> list[str]:
    """
    Prompt the user for the allowed algorithm stores on their node

    Returns
    -------
    list[str]
        List of allowed algorithm stores
    """
    info("Below you can add algorithm stores that are allowed to run on your node.")
    info(
        "You can use regular expressions to match multiple algorithm stores, or you can"
        " use strings to provide one algorithm store at a time."
    )
    info("Examples:")
    info(
        "https://store.cotopaxi.vantage6.ai    Allow all algorithms from the "
        "community store"
    )
    info(
        r"^https://*\.vantage6\.ai$               Allow all algorithms from any "
        "store hosted on vantage6.ai"
    )
    allowed_algorithm_stores = []
    while True:
        store = q.text(message="Enter the URL of the algorithm store:").unsafe_ask()
        allowed_algorithm_stores.append(store)
        if not q.confirm(
            "Do you want to add another algorithm store?", default=True
        ).unsafe_ask():
            break
    return allowed_algorithm_stores


def _get_common_server_config(instance_type: InstanceType, instance_name: str) -> dict:
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
    config = q.unsafe_prompt(
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
                    str(Ports.DEV_SERVER.value)
                    if instance_type == InstanceType.SERVER
                    else str(Ports.DEV_ALGO_STORE.value)
                ),
            },
        ]
    )

    config.update(
        q.unsafe_prompt(
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
    ).unsafe_ask()

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

    config["api_path"] = DEFAULT_API_PATH

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

    config = _get_common_server_config(InstanceType.SERVER, instance_name)

    constant_jwt_secret = q.confirm("Do you want a constant JWT secret?").unsafe_ask()
    if constant_jwt_secret:
        config["jwt_secret_key"] = generate_apikey()

    is_mfa = q.confirm("Do you want to enforce two-factor authentication?").unsafe_ask()
    if is_mfa:
        config["two_factor_auth"] = is_mfa

    current_server_url = f"http://localhost:{config['port']}{config['api_path']}"
    config["server_url"] = q.text(
        "What is the server url exposed to the users? If you are running a"
        " development server running locally, this is the same as the "
        "server url. If you are running a production server, this is the "
        "url that users will connect to.",
        default=current_server_url,
    ).unsafe_ask()

    is_add_vpn = q.confirm(
        "Do you want to add a VPN server?", default=False
    ).unsafe_ask()
    if is_add_vpn:
        vpn_config = q.unsafe_prompt(
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

    is_add_rabbitmq = q.confirm(
        "Do you want to add a RabbitMQ message queue?"
    ).unsafe_ask()
    if is_add_rabbitmq:
        rabbit_uri = q.text(message="Enter the URI for your RabbitMQ:").unsafe_ask()
        run_rabbit_locally = q.confirm(
            "Do you want to run RabbitMQ locally? (Use only for testing)"
        ).unsafe_ask()
        config["rabbitmq"] = {
            "uri": rabbit_uri,
            "start_with_server": run_rabbit_locally,
        }

    # add algorithm stores to this server
    is_add_community_store = q.confirm(
        "Do you want to make the algorithms from the community algorithm store "
        "available to your users?"
    ).unsafe_ask()
    algorithm_stores = []
    if is_add_community_store:
        algorithm_stores.append(
            {"name": "Community store", "url": "https://store.cotopaxi.vantage6.ai"}
        )
    add_more_stores = q.confirm(
        "Do you want to add more algorithm stores?", default=False
    ).unsafe_ask()
    while add_more_stores:
        store_name = q.text(message="Enter the name of the store:").unsafe_ask()
        store_url = q.text(message="Enter the URL of the store:").unsafe_ask()
        algorithm_stores.append({"name": store_name, "url": store_url})
        add_more_stores = q.confirm(
            "Do you want to add more algorithm stores?", default=False
        ).unsafe_ask()
    config["algorithm_stores"] = algorithm_stores

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
    config = _get_common_server_config(InstanceType.ALGORITHM_STORE, instance_name)

    default_v6_server_uri = (
        f"http://localhost:{Ports.DEV_SERVER.value}{DEFAULT_API_PATH}"
    )
    default_root_username = "root"

    v6_server_uri = q.text(
        "What is the Vantage6 server linked to the algorithm store? "
        "Provide the link to the server endpoint.",
        default=default_v6_server_uri,
    ).unsafe_ask()

    root_username = q.text(
        "What is the username of the root user?",
        default=default_root_username,
    ).unsafe_ask()

    config["root_user"] = {
        "v6_server_uri": v6_server_uri,
        "username": root_username,
    }

    # ask about openness of the algorithm store
    config["policies"] = {"allow_localhost": False}
    is_open = q.confirm(
        "Do you want to open the algorithm store to the public? This will allow anyone "
        "to view the algorithms, but they cannot modify them.",
        default=False,
    ).unsafe_ask()
    if is_open:
        open_algos_policy = "public"
    else:
        is_open_to_whitelist = q.confirm(
            "Do you want to allow all users of whitelisted vantage6 servers to access "
            "the algorithms in the store? If not allowing this, you will have to assign"
            " the appropriate permissions to each user individually.",
            default=True,
        ).unsafe_ask()
        open_algos_policy = "whitelisted" if is_open_to_whitelist else "private"
    config["policies"]["algorithm_view"] = open_algos_policy

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
    try:
        return q.select(
            "Select the configuration you want to use:", choices=choices
        ).unsafe_ask()
    except KeyboardInterrupt:
        error("Aborted by user!")
        exit(1)
