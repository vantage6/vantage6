"""
Common functions that are used in node CLI commands
"""

import os

import docker
from colorama import Fore, Style

from vantage6.common import debug, error, info
from vantage6.common.globals import APPNAME, InstanceType, RequiredNodeEnvVars

from vantage6.client import UserClient

from vantage6.cli.configuration_wizard import select_configuration_questionaire
from vantage6.cli.context.node import NodeContext


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
    return UserClient(
        server_url=f"{host}:{port}{api_path}",
        auth_url=os.environ.get(RequiredNodeEnvVars.KEYCLOAK_URL.value),
        log_level="warn",
    )


def create_client_and_authenticate(ctx: NodeContext) -> UserClient:
    """
    Generate a client and authenticate with the server.

    Parameters
    ----------
    ctx : NodeContext
        Context of the node loaded from the configuration file

    Returns
    -------
    UserClient
        vantage6 client
    """
    client = create_client(ctx)

    try:
        client.authenticate()
    except Exception as exc:
        error("Could not authenticate with server!")
        debug(exc)
        exit(1)

    return client


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
            f"The configuration {Fore.RED}{name}{Style.RESET_ALL} could not be found."
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
        filters={"label": f"{APPNAME}-type={InstanceType.NODE.value}"}
    )
    return [node.name for node in running_nodes]
