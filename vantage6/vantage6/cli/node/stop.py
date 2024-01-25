import click
import questionary as q
import docker

from colorama import Fore, Style

from vantage6.common import warning, error, info
from vantage6.common.globals import APPNAME
from vantage6.common.docker.addons import check_docker_running
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
        for name in running_node_names:
            container = client.containers.get(name)
            if force:
                container.kill()
            else:
                container.stop()
            info(f"Stopped the {Fore.GREEN}{name}{Style.RESET_ALL} Node.")
    else:
        if not name:
            name = q.select(
                "Select the node you wish to stop:", choices=running_node_names
            ).ask()
        else:
            post_fix = "system" if system_folders else "user"
            name = f"{APPNAME}-{name}-{post_fix}"

        if name in running_node_names:
            container = client.containers.get(name)
            # Stop the container. Using stop() gives the container 10s to exit
            # itself, if not then it will be killed
            if force:
                container.kill()
            else:
                container.stop()
            info(f"Stopped the {Fore.GREEN}{name}{Style.RESET_ALL} Node.")
        else:
            error(f"{Fore.RED}{name}{Style.RESET_ALL} is not running?")
