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
@click.option("--all", "all_stores", flag_value=True, help="Stop all algorithm stores")
def cli_algo_store_stop(
    name: str,
    context: str,
    namespace: str,
    system_folders: bool,
    all_stores: bool,
):
    """
    Stop one or all running algorithm store(s).
    """
    execute_stop(
        stop_function=_stop_store,
        instance_type=InstanceType.ALGORITHM_STORE,
        infra_component=InfraComponentName.ALGORITHM_STORE,
        stop_all=all_stores,
        to_stop=name,
        namespace=namespace,
        context=context,
        system_folders=system_folders,
    )


def _stop_store(store_name: str, namespace: str, context: str) -> None:
    info(f"Stopping store {store_name}...")

    helm_uninstall(release_name=store_name, context=context, namespace=namespace)

    stop_port_forward(service_name=f"{store_name}-store-service")

    info(f"Store {store_name} stopped successfully.")
