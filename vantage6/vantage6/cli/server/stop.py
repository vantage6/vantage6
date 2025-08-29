import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.stop import execute_stop, helm_uninstall, stop_port_forward
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS, InfraComponentName


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
@click.option("--all", "all_servers", flag_value=True, help="Stop all running servers")
def cli_server_stop(
    name: str,
    context: str,
    namespace: str,
    system_folders: bool,
    all_servers: bool,
):
    """
    Stop an running server.
    """
    execute_stop(
        stop_function=_stop_server,
        instance_type=InstanceType.SERVER,
        infra_component=InfraComponentName.SERVER,
        stop_all=all_servers,
        to_stop=name,
        namespace=namespace,
        context=context,
        system_folders=system_folders,
    )


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
