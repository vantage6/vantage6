import click
import docker

from colorama import (Fore, Style)

from vantage6.common import warning
from vantage6.common.docker.addons import check_docker_running
from vantage6.common.globals import APPNAME
from vantage6.cli.context import ServerContext


@click.command()
def cli_server_configuration_list() -> None:
    """
    Print the available server configurations.
    """
    check_docker_running()
    client = docker.from_env()

    running_server = client.containers.list(
        filters={"label": f"{APPNAME}-type=server"})
    running_node_names = []
    for node in running_server:
        running_node_names.append(node.name)

    header = \
        "\nName"+(21*" ") + \
        "Status"+(10*" ") + \
        "System/User"

    click.echo(header)
    click.echo("-"*len(header))

    running = Fore.GREEN + "Running" + Style.RESET_ALL
    stopped = Fore.RED + "Not running" + Style.RESET_ALL

    # system folders
    configs, f1 = ServerContext.available_configurations(system_folders=True)
    for config in configs:
        status = running if f"{APPNAME}-{config.name}-system-server" in \
            running_node_names else stopped
        click.echo(
            f"{config.name:25}"
            f"{status:25} System "
        )

    # user folders
    configs, f2 = ServerContext.available_configurations(system_folders=False)
    for config in configs:
        status = running if f"{APPNAME}-{config.name}-user-server" in \
            running_node_names else stopped
        click.echo(
            f"{config.name:25}"
            f"{status:25} User   "
        )

    click.echo("-"*85)
    if len(f1)+len(f2):
        warning(
             f"{Fore.RED}Failed imports: {len(f1)+len(f2)}{Style.RESET_ALL}")
