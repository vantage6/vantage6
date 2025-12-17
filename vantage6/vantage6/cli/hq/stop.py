import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.stop import execute_stop, helm_uninstall
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS, InfraComponentName
from vantage6.cli.k8s_config import KubernetesConfig


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
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click.option("--all", "all_servers", flag_value=True, help="Stop all running servers")
def cli_server_stop(
    name: str,
    context: str,
    namespace: str,
    system_folders: bool,
    sandbox: bool,
    all_servers: bool,
):
    """
    Stop an running server.
    """
    execute_stop(
        stop_function=_stop_server,
        instance_type=InstanceType.HQ,
        infra_component=InfraComponentName.HQ,
        stop_all=all_servers,
        to_stop=name,
        namespace=namespace,
        context=context,
        system_folders=system_folders,
        is_sandbox=sandbox,
    )


def _stop_server(server_name: str, k8s_config: KubernetesConfig) -> None:
    info(f"Stopping server {server_name}...")

    # uninstall the helm release
    helm_uninstall(
        release_name=server_name,
        k8s_config=k8s_config,
    )

    info(f"Server {server_name} stopped successfully.")
