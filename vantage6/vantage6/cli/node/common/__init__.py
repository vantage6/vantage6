"""
Common functions that are used in node CLI commands
"""

import questionary as q
import docker
from colorama import Fore, Style

from vantage6.common import error, info, debug
from vantage6.common.globals import APPNAME, InstanceType
from vantage6.client import UserClient

from vantage6.cli.context.node import NodeContext
from vantage6.cli.configuration_wizard import select_configuration_questionaire


def create_client(ctx: NodeContext) -> UserClient:
    """
    Create a client instance.

    Parameters
    ----------
    ctx : NodeContext
        Context of the node loaded from the configuration file
    Returns
    -------
    UserClient
        vantage6 client
    """
    host = ctx.config["server_url"]
    # if the server is run locally, we need to use localhost here instead of
    # the host address of docker
    if host in ["http://host.docker.internal", "http://172.17.0.1"]:
        host = "http://localhost"
    port = ctx.config["port"]
    api_path = ctx.config["api_path"]
    info(f"Connecting to server at '{host}:{port}{api_path}'")
    return UserClient(host, port, api_path, log_level="warn")


def create_client_and_authenticate(
    ctx: NodeContext, ask_mfa: bool = False
) -> UserClient:
    """
    Generate a client and authenticate with the server.

    Parameters
    ----------
    ctx : NodeContext
        Context of the node loaded from the configuration file
    ask_mfa : bool, optional
        Whether to ask for MFA code, by default False

    Returns
    -------
    UserClient
        vantage6 client
    """
    client = create_client(ctx)

    try:
        username, password, mfa_code = _get_auth_data()
    except KeyboardInterrupt:
        error("Authentication aborted.")
        exit(1)

    try:
        client.authenticate(username, password, mfa_code=mfa_code)

    except Exception as exc:
        error("Could not authenticate with server!")
        debug(exc)
        exit(1)

    return client


def _get_auth_data() -> tuple[str, str, str]:
    """
    Get authentication data from the user.

    Returns
    -------
    tuple[str, str, str]
        Tuple containing username, password and MFA code
    """
    username = q.text("Username:").unsafe_ask()
    password = q.password("Password:").unsafe_ask()
    mfa_code = q.text("MFA code:").unsafe_ask()
    return username, password, mfa_code


def select_node(name: str, system_folders: bool) -> tuple[str, str]:
    """
    Let user select node through questionnaire if name is not given.

    Returns
    -------
    str
        Name of the configuration file
    """
    name = (
        name
        if name
        else select_configuration_questionaire(InstanceType.NODE, system_folders)
    )

    # raise error if config could not be found
    if not NodeContext.config_exists(name, system_folders):
        error(
            f"The configuration {Fore.RED}{name}{Style.RESET_ALL} could "
            f"not be found."
        )
        exit(1)
    return name


def find_running_node_names(client: docker.DockerClient) -> list[str]:
    """
    Returns a list of names of running nodes.

    Parameters
    ----------
    client : docker.DockerClient
        Docker client instance

    Returns
    -------
    list[str]
        List of names of running nodes
    """
    running_nodes = client.containers.list(
        filters={"label": f"{APPNAME}-type={InstanceType.NODE}"}
    )
    return [node.name for node in running_nodes]
