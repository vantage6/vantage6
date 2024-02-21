import click
import docker

from colorama import Fore, Style

from vantage6.common import error
from vantage6.common.docker.addons import check_docker_running
from vantage6.common.globals import APPNAME, InstanceType
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import attach_logs
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext


@click.command()
@click_insert_context(InstanceType.ALGORITHM_STORE)
def cli_algo_store_attach(ctx: AlgorithmStoreContext) -> None:
    """
    Show the server logs in the current console.
    """
    check_docker_running()
    client = docker.from_env()

    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type={InstanceType.ALGORITHM_STORE}"}
    )
    running_server_names = [container.name for container in running_servers]

    if ctx.docker_container_name in running_server_names:
        container = client.containers.get(ctx.docker_container_name)
        attach_logs(container, InstanceType.ALGORITHM_STORE)
    else:
        error(f"{Fore.RED}{ctx.name}{Style.RESET_ALL} is not running!")
