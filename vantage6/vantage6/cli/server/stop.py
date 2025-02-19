import click
import questionary as q
import docker
from colorama import Fore, Style
from docker.client import DockerClient

from vantage6.common import info, warning, error
from vantage6.common.docker.addons import (
    check_docker_running,
    remove_container,
    get_server_config_name,
    get_container,
    get_num_nonempty_networks,
    get_network,
    delete_network,
    remove_container_if_exists,
)
from vantage6.common.globals import APPNAME, InstanceType
from vantage6.common import split_rabbitmq_uri
from vantage6.cli.context.server import ServerContext
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS
from vantage6.cli.server.common import get_server_context, stop_ui


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--system", "system_folders", flag_value=True)
@click.option(
    "--user", "system_folders", flag_value=False, default=DEFAULT_SERVER_SYSTEM_FOLDERS
)
@click.option("--all", "all_servers", flag_value=True, help="Stop all servers")
def cli_server_stop(name: str, system_folders: bool, all_servers: bool):
    """
    Stop one or all running server(s).
    """
    check_docker_running()
    client = docker.from_env()

    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type={InstanceType.SERVER}"}
    )

    if not running_servers:
        warning("No servers are currently running.")
        return

    running_server_names = [server.name for server in running_servers]

    if all_servers:
        for container_name in running_server_names:
            _stop_server_containers(client, container_name, system_folders)
        return

    # make sure we have a configuration name to work with
    if not name:
        try:
            container_name = q.select(
                "Select the server you wish to stop:", choices=running_server_names
            ).unsafe_ask()
        except KeyboardInterrupt:
            error("Aborted by user!")
            return
    else:
        post_fix = "system" if system_folders else "user"
        container_name = f"{APPNAME}-{name}-{post_fix}-{InstanceType.SERVER}"

    if container_name not in running_server_names:
        error(f"{Fore.RED}{name}{Style.RESET_ALL} is not running!")
        return

    _stop_server_containers(client, container_name, system_folders)


def _stop_server_containers(
    client: DockerClient, container_name: str, system_folders: bool
) -> None:
    """
    Given a server's name, kill its docker container and related (RabbitMQ)
    containers.

    Parameters
    ----------
    client : DockerClient
        Docker client
    container_name : str
        Name of the server to stop
    system_folders : bool
        Wether to use system folders or not
    """
    # kill the server
    remove_container_if_exists(client, name=container_name)
    info(f"Stopped the {Fore.GREEN}{container_name}{Style.RESET_ALL} server.")

    # find the configuration name from the docker container name
    scope = "system" if system_folders else "user"
    config_name = get_server_config_name(container_name, scope)

    ctx = get_server_context(config_name, system_folders, ServerContext)

    # kill the UI container (if it exists)
    stop_ui(client, ctx)

    # delete the server network
    network_name = f"{APPNAME}-{ctx.name}-{ctx.scope}-network"
    network = get_network(client, name=network_name)
    delete_network(network, kill_containers=False)

    # kill RabbitMQ if it exists and no other servers are using to it (i.e. it
    # is not in other docker networks with other containers)
    rabbit_uri = ctx.config.get("rabbitmq", {}).get("uri")
    if rabbit_uri:
        rabbit_container_name = split_rabbitmq_uri(rabbit_uri=rabbit_uri)["host"]
        rabbit_container = get_container(client, name=rabbit_container_name)
        if rabbit_container and get_num_nonempty_networks(rabbit_container) == 0:
            remove_container(rabbit_container, kill=True)
            info(
                f"Stopped the {Fore.GREEN}{rabbit_container_name}"
                f"{Style.RESET_ALL} container."
            )
