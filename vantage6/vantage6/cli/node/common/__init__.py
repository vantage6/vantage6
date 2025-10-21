"""
Common functions that are used in node CLI commands
"""

import os

import docker
from colorama import Fore, Style

from vantage6.common import debug, error, info
from vantage6.common.globals import (
    APPNAME,
    HTTP_LOCALHOST,
    InstanceType,
    Ports,
    RequiredNodeEnvVars,
)

from vantage6.client import UserClient

from vantage6.cli.configuration_create import select_configuration_questionnaire
from vantage6.cli.context.node import NodeContext


def convert_k8s_url_to_localhost(url: str) -> str:
    """
    Convert a Kubernetes URL to a localhost URL.
    """
    if "svc.cluster.local" in url:
        port_and_api_path = url.split(":")[-1]
        return f"{HTTP_LOCALHOST}:{port_and_api_path}"
    return url


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
    host = ctx.config["node"]["server"]["url"]
    port = ctx.config["node"]["server"]["port"]
    api_path = ctx.config["node"]["server"]["path"]
    # if the server is run locally, we need to use localhost here instead of
    # the host address of docker
    if host in ["http://host.docker.internal", "http://172.17.0.1"]:
        host = HTTP_LOCALHOST

    url = f"{host}:{port}{api_path}"

    auth_url = ctx.config.get("node", {}).get("keycloakUrl", None) or os.environ.get(
        RequiredNodeEnvVars.KEYCLOAK_URL.value
    )
    # append the port to the auth URL as it is not included in the config
    auth_url = f"{auth_url}:{Ports.DEV_AUTH.value}"

    # if the server is a Kubernetes address, we need to use localhost because here
    # we are connecting from the CLI outside the cluster
    url = convert_k8s_url_to_localhost(url)
    auth_url = convert_k8s_url_to_localhost(auth_url)

    info(f"Connecting to server at '{url}' using auth URL '{auth_url}'")
    return UserClient(
        server_url=url,
        auth_url=auth_url,
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
        debug(str(exc))
        exit(1)

    return client


def select_node(name: str, system_folders: bool) -> str:
    """
    Let user select node through questionnaire if name is not given.

    Parameters
    ----------
    name : str
        Name of the node to select
    system_folders : bool
        Whether to use system folders or not

    Returns
    -------
    str
        Name of the configuration file
    """
    try:
        name = (
            name
            if name
            else select_configuration_questionnaire(InstanceType.NODE, system_folders)
        )
    except Exception:
        error("No configurations could be found!")
        exit()

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
