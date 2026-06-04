"""
Common functions that are used in node CLI commands
"""

import os

from colorama import Fore, Style

from vantage6.common import debug, error, info
from vantage6.common.globals import (
    HTTP_LOCALHOST,
    InstanceType,
    Ports,
    RequiredNodeEnvVars,
)

from vantage6.client import UserClient
from vantage6.client.utils import LogLevel

from vantage6.cli.configuration_create import select_configuration_questionnaire
from vantage6.cli.context.node import NodeContext


def _convert_k8s_url_to_localhost(url: str) -> str:
    """
    Convert a Kubernetes URL to a localhost URL.
    """
    if "svc.cluster.local" in url:
        port_and_api_path = url.split(":")[-1]
        return f"{HTTP_LOCALHOST}:{port_and_api_path}"
    return url


def create_client(ctx: NodeContext, use_sandbox_port: bool = False) -> UserClient:
    """
    Create a client instance.

    Parameters
    ----------
    ctx : NodeContext
        Context of the node loaded from the configuration file
    use_sandbox_port : bool
        Whether to use the sandbox port or not

    Returns
    -------
    UserClient
        vantage6 client
    """
    host = ctx.config["node"]["hq"]["url"]
    port = ctx.config["node"]["hq"]["port"]
    api_path = ctx.config["node"]["hq"]["path"]
    # if the hq is run locally in Docker, we need to use localhost here instead of
    # the host address of docker
    if host in ["http://host.docker.internal", "http://172.17.0.1"]:
        host = HTTP_LOCALHOST

    url = f"{host}:{port}{api_path}"

    auth_url = ctx.config.get("node", {}).get("keycloak", {}).get(
        "url", None
    ) or os.environ.get(RequiredNodeEnvVars.KEYCLOAK_URL.value)
    # append the port to the auth URL as it is not included in the config
    if use_sandbox_port:
        auth_url = f"{auth_url}:{Ports.SANDBOX_AUTH.value}"
    else:
        auth_url = f"{auth_url}:{Ports.DEV_AUTH.value}"

    # if the URL is a Kubernetes address, we need to use localhost because here
    # we are connecting from the CLI outside the cluster
    url = _convert_k8s_url_to_localhost(url)
    auth_url = _convert_k8s_url_to_localhost(auth_url)

    info(f"Connecting to HQ at '{url}' using auth URL '{auth_url}'")
    return UserClient(
        hq_url=url,
        auth_url=auth_url,
        log_level=LogLevel.WARN,
    )


def create_client_and_authenticate(
    ctx: NodeContext, use_sandbox_port: bool = False
) -> UserClient:
    """
    Generate a client and authenticate.

    Parameters
    ----------
    ctx : NodeContext
        Context of the node loaded from the configuration file
    use_sandbox_port : bool
        Whether to use the sandbox port or not

    Returns
    -------
    UserClient
        vantage6 client
    """
    client = create_client(ctx, use_sandbox_port)

    try:
        client.authenticate()
    except Exception as exc:
        error("Could not authenticate!")
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
