import os
from pathlib import Path

import click
import questionary as q

from vantage6.common import error, info, warning
from vantage6.common.client.node_client import NodeClient
from vantage6.common.globals import (
    FILE_BASED_DATABASE_TYPES,
    SERVICE_BASED_DATABASE_TYPES,
    InstanceType,
    NodePolicy,
    Ports,
    RequiredNodeEnvVars,
)

from vantage6.cli.common.new import new
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Store this configuration in the system folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Store this configuration in the user folders. This is the default.",
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option(
    "--namespace",
    default=None,
    help="Kubernetes namespace to use",
)
def cli_node_new_configuration(
    name: str,
    system_folders: bool,
    namespace: str,
    context: str,
) -> None:
    """
    Create a new node configuration.

    Checks if the configuration already exists. If this is not the case
    a questionnaire is invoked to create a new configuration file.
    """
    new(
        questionnaire_function=node_configuration_questionaire,
        name=name,
        system_folders=system_folders,
        namespace=namespace,
        context=context,
        type_=InstanceType.NODE,
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
        str(Ports.HTTPS)
        if config["server_url"].startswith("https")
        else str(Ports.DEV_SERVER)
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

    config["databases"] = {"fileBased": [], "serviceBased": []}
    while q.confirm("Do you want to add a database?").unsafe_ask():
        db_label = q.select(
            "What type of database do you want to add?",
            choices=["File database", "Database reachable by URI"],
        ).unsafe_ask()

        if db_label == "File database":
            config["databases"]["fileBased"].append(_get_file_based_database_config())
        else:
            config["databases"]["serviceBased"].append(
                _get_service_based_database_config()
            )

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
    client = NodeClient(
        instance_name,
        config["api_key"],
        server_url=f"{config['server_url']}:{config['port']}{config['api_path']}",
        auth_url=os.environ.get(RequiredNodeEnvVars.KEYCLOAK_URL.value),
    )
    try:
        client.authenticate()
    except Exception as e:
        error(f"Could not authenticate with server: {e}")
        error("Please check (1) your API key and (2) if your server is online")
        warning(
            "If you continue, you should provide your collaboration settings manually."
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

    # pack the entire config in a dict with the 'node' key at top level
    return {"node": config}


def _get_file_based_database_config() -> dict:
    """
    Prompt the user for the file-based database configuration
    """
    db_label = _get_database_label()
    while True:
        db_path = q.text(
            "Path to the database file:",
        ).unsafe_ask()
        if Path(db_path).exists():
            break
        else:
            error("The path to the database file does not exist. Please try again.")
    db_path_resolved = Path(db_path).resolve()
    db_dir = db_path_resolved.parent
    db_filename = db_path_resolved.name
    db_type = q.select("Database type:", choices=FILE_BASED_DATABASE_TYPES).unsafe_ask()
    return {
        "name": db_label,
        "uri": db_path,
        "type": db_type,
        "volumePath": db_dir,
        "originalName": db_filename,
    }


def _get_service_based_database_config() -> dict:
    """
    Prompt the user for the service-based database configuration

    Returns
    -------
    dict
        Dictionary with the service-based database configuration
    """
    db_label = _get_database_label()
    db_uri = q.text(
        "Database URI:",
    ).unsafe_ask()
    db_type = q.select(
        "Database type:", choices=SERVICE_BASED_DATABASE_TYPES
    ).unsafe_ask()

    env_vars = {}
    info("You can add environment variables to the database configuration.")
    info("These variables will be available to the algorithms on your node.")
    info("Example: MY_POSTGRES_USER=vantage6, MY_POSTGRES_PASSWORD=vantage6")
    while q.confirm("Do you want to add an environment variable?").unsafe_ask():
        env_var_name = q.text(
            "Enter the name of the environment variable:"
        ).unsafe_ask()
        env_var_value = q.text(
            "Enter the value of the environment variable:"
        ).unsafe_ask()
        env_vars[env_var_name] = env_var_value

    return {
        "name": db_label,
        "uri": db_uri,
        "type": db_type,
        "env": env_vars,
    }


def _get_database_label() -> str:
    """
    Prompt the user for the label of the database
    """
    return q.text(
        "Enter unique label for the database:",
        default="default",
    ).unsafe_ask()


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
