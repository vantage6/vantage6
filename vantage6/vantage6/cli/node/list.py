import click
import docker
from colorama import Fore, Style

from vantage6.common import warning
from vantage6.common.globals import APPNAME
from vantage6.common.docker.addons import check_docker_running
from vantage6.cli.context.node import NodeContext
from vantage6.cli.node.common import find_running_node_names


@click.command()
def cli_node_list() -> None:
    """
    Lists all node configurations.

    Note that this command cannot find node configuration files in custom
    directories.
    """

    check_docker_running()
    client = docker.from_env()

    running_node_names = find_running_node_names(client)

    header = "\nName" + (21 * " ") + "Status" + (10 * " ") + "System/User"

    click.echo(header)
    click.echo("-" * len(header))

    running = Fore.GREEN + "Running" + Style.RESET_ALL
    stopped = Fore.RED + "Not running" + Style.RESET_ALL

    # system folders
    configs, f1 = NodeContext.available_configurations(system_folders=True)
    for config in configs:
        status = (
            running
            if f"{APPNAME}-{config.name}-system" in running_node_names
            else stopped
        )
        click.echo(f"{config.name:25}" f"{status:25}System ")

    # user folders
    configs, f2 = NodeContext.available_configurations(system_folders=False)
    for config in configs:
        status = (
            running
            if f"{APPNAME}-{config.name}-user" in running_node_names
            else stopped
        )
        click.echo(f"{config.name:25}" f"{status:25}User   ")

    click.echo("-" * 53)
    if len(f1) + len(f2):
        warning(f"{Fore.RED}Failed imports: {len(f1)+len(f2)}{Style.RESET_ALL}")
