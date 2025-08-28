import click
from colorama import Fore, Style

from vantage6.common import error, info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.stop import helm_uninstall, stop_port_forward
from vantage6.cli.common.utils import (
    find_running_service_names,
    select_context_and_namespace,
    select_running_service,
)
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
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    running_stores = find_running_service_names(
        instance_type=InstanceType.ALGORITHM_STORE,
        only_system_folders=system_folders,
        only_user_folders=not system_folders,
        context=context,
        namespace=namespace,
    )

    if not running_stores:
        error("No running algorithm stores found.")
        return

    if all_stores:
        for store in running_stores:
            _stop_store(store["name"], namespace, context)
    else:
        if not name:
            store_name = select_running_service(
                running_stores, InstanceType.ALGORITHM_STORE
            )
        else:
            ctx = get_context(InstanceType.ALGORITHM_STORE, name, system_folders)
            store_name = ctx.helm_release_name

        if store_name in running_stores:
            _stop_store(store_name, namespace, context)
            info(f"Stopped the {Fore.GREEN}{store_name}{Style.RESET_ALL} store.")
        else:
            error(f"{Fore.RED}{name}{Style.RESET_ALL} is not running?!")


def _stop_store(store_name: str, namespace: str, context: str) -> None:
    info(f"Stopping store {store_name}...")

    # uninstall the helm release
    helm_uninstall(
        release_name=store_name,
        context=context,
        namespace=namespace,
    )

    stop_port_forward(
        service_name=f"{store_name}-vantage6-algorithm-store-service",
    )

    info(f"Store {store_name} stopped successfully.")
