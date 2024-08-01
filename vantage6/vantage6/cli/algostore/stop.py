import click
import docker
from colorama import Fore, Style

from vantage6.common import info, warning, error
from vantage6.common.docker.addons import (
    check_docker_running,
    remove_container_if_exists,
)
from vantage6.common.globals import APPNAME, InstanceType
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext


@click.command()
@click_insert_context(InstanceType.ALGORITHM_STORE)
@click.option("--all", "all_stores", flag_value=True, help="Stop all algorithm stores")
def cli_algo_store_stop(ctx: AlgorithmStoreContext, all_stores: bool):
    """
    Stop one or all running server(s).
    """
    check_docker_running()
    client = docker.from_env()

    running_stores = client.containers.list(
        filters={"label": f"{APPNAME}-type={InstanceType.ALGORITHM_STORE}"}
    )

    if not running_stores:
        warning("No algorithm stores are currently running.")
        return

    running_store_names = [server.name for server in running_stores]

    if all_stores:
        for container_name in running_store_names:
            _stop_algorithm_store(client, container_name)
        return

    container_name = ctx.docker_container_name
    if container_name not in running_store_names:
        error(f"{Fore.RED}{ctx.name}{Style.RESET_ALL} is not running!")
        return

    _stop_algorithm_store(client, container_name)


def _stop_algorithm_store(client, container_name) -> None:
    """
    Stop the algorithm store server.

    Parameters
    ----------
    client : DockerClient
        The docker client
    container_name : str
        The name of the container to stop
    """
    remove_container_if_exists(client, name=container_name)
    info(f"Stopped the {Fore.GREEN}{container_name}{Style.RESET_ALL} server.")
