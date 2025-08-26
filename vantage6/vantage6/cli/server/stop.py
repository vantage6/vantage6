import click
import questionary as q
from colorama import Fore, Style

from vantage6.common import error, info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.stop import helm_uninstall, stop_port_forward
from vantage6.cli.common.utils import find_running_service_names
from vantage6.cli.config import CliConfig
from vantage6.cli.context import get_context
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    default=DEFAULT_SERVER_SYSTEM_FOLDERS,
    help="Search for configuration in system folders instead of user folders. "
    "This is the default.",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    help="Search for configuration in the user folders instead of system folders.",
)
@click.option("--all", "all", flag_value=True, help="Stop all running servers")
def cli_server_stop(
    name: str,
    context: str,
    namespace: str,
    system_folders: bool,
    all: bool,
):
    """
    Stop an running server.
    """
    cli_config = CliConfig()

    context, namespace = cli_config.compare_changes_config(
        context=context,
        namespace=namespace,
    )

    running_servers = find_running_service_names(
        instance_type=InstanceType.SERVER,
        only_system_folders=system_folders,
        only_user_folders=not system_folders,
        context=context,
        namespace=namespace,
    )

    if not running_servers:
        error("No running servers found.")
        return

    if all:
        for server in running_servers:
            _stop_server(server["name"], namespace, context)
    else:
        if not name:
            try:
                server_name = q.select(
                    "Select the server you wish to stop:", choices=running_servers
                ).unsafe_ask()
            except KeyboardInterrupt:
                error("Aborted by user!")
                return
        else:
            ctx = get_context(InstanceType.SERVER, name, system_folders)
            server_name = ctx.helm_release_name

        if server_name in running_servers:
            _stop_server(server_name, namespace, context)
            info(f"Stopped the {Fore.GREEN}{server_name}{Style.RESET_ALL} Server.")
        else:
            error(f"{Fore.RED}{name}{Style.RESET_ALL} is not running?!")


def _stop_server(server_name: str, namespace: str, context: str) -> None:
    info(f"Stopping server {server_name}...")

    # uninstall the helm release
    helm_uninstall(
        release_name=server_name,
        context=context,
        namespace=namespace,
    )

    # stop the port forwarding for server and UI
    stop_port_forward(
        service_name=f"{server_name}-vantage6-server-service",
    )

    stop_port_forward(
        service_name=f"{server_name}-vantage6-frontend-service",
    )

    info(f"Server {server_name} stopped successfully.")
