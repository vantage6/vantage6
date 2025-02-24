import time
import click
import questionary as q
import docker

from colorama import Fore, Style
from vantage6.cli.context import NodeContext

from vantage6.common import warning, error, info
from vantage6.common.globals import APPNAME
from vantage6.common.docker.addons import (
    check_docker_running,
    delete_volume_if_exists,
    get_server_config_name,
    stop_container,
)
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL

from vantage6.cli.node.common import find_running_node_names


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Search for configuration in system folders instead of " "user folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Search for configuration in the user folders instead of "
    "system folders. This is the default.",
)
@click.option("--all", "all_nodes", flag_value=True, help="Stop all running nodes")
@click.option(
    "--force",
    "force",
    flag_value=True,
    help="Kill nodes instantly; don't wait for them to shut down",
)
def cli_node_stop(
    name: str, system_folders: bool, all_nodes: bool, force: bool
) -> None:
    """
    Stop one or all running nodes.
    """
    check_docker_running()
    client = docker.from_env()

    running_node_names = find_running_node_names(client)

    if not running_node_names:
        warning("No nodes are currently running.")
        return

    if force:
        warning(
            "Forcing the node to stop will not terminate helper "
            "containers, neither will it remove routing rules made on the "
            "host!"
        )

    if all_nodes:
        for container_name in running_node_names:
            _stop_node(client, container_name, force, system_folders)
    else:
        if not name:
            try:
                container_name = q.select(
                    "Select the node you wish to stop:", choices=running_node_names
                ).unsafe_ask()
            except KeyboardInterrupt:
                error("Aborted by user!")
                return
        else:
            post_fix = "system" if system_folders else "user"
            container_name = f"{APPNAME}-{name}-{post_fix}"

        if container_name in running_node_names:
            _stop_node(client, container_name, force, system_folders)
            info(f"Stopped the {Fore.GREEN}{container_name}{Style.RESET_ALL} Node.")
        else:
            error(f"{Fore.RED}{name}{Style.RESET_ALL} is not running?!")


def _stop_node(
    client: docker.DockerClient, container_name: str, force: bool, system_folders: bool
) -> None:
    """
    Stop a node

    Parameters
    ----------
    client : docker.DockerClient
        Docker client
    name : str
        Name of the node container to stop
    force : bool
        Whether to force the node to stop
    system_folders : bool
        Whether to use system folders or not
    """
    container = client.containers.get(container_name)
    # Stop the container. Using stop() gives the container 10s to exit
    # itself, if not then it will be killed
    stop_container(container, force)

    # Sleep for 1 second. Not doing so often causes errors that docker volumes deleted
    # below are 'still in use' when you try to remove them a few ms after the container
    # has been removed
    time.sleep(1)

    # Delete volumes. This is done here rather than within the node container when
    # it is stopped, because at that point the volumes are still in use. Here, the node
    # has already been stopped
    scope = "system" if system_folders else "user"
    config_name = get_server_config_name(container_name, scope)
    ctx = NodeContext(config_name, system_folders, print_log_header=False)

    # Do not delete the data volume as this would remove all sessions.
    for volume in [
        # ctx.docker_volume_name,
        ctx.docker_squid_volume_name,
        ctx.docker_ssh_volume_name,
        ctx.docker_vpn_volume_name,
    ]:
        delete_volume_if_exists(client, volume)
