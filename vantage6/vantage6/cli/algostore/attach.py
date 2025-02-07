import click
import docker
import questionary as q

from colorama import Fore, Style

from vantage6.common import error
from vantage6.common.docker.addons import check_docker_running
from vantage6.common.globals import APPNAME, InstanceType
from vantage6.cli.common.start import attach_logs
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS


@click.command()
@click.option("-n", "--name", default=None, help="configuration name")
@click.option("--system", "system_folders", flag_value=True)
@click.option(
    "--user", "system_folders", flag_value=False, default=DEFAULT_SERVER_SYSTEM_FOLDERS
)
def cli_algo_store_attach(name: str, system_folders: bool) -> None:
    """
    Show the server logs in the current console.
    """
    check_docker_running()
    client = docker.from_env()

    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type={InstanceType.ALGORITHM_STORE}"}
    )
    running_server_names = [container.name for container in running_servers]

    if not name:
        try:
            name = q.select(
                "Select the algorithm store you wish to attach:",
                choices=running_server_names,
            ).unsafe_ask()
        except KeyboardInterrupt:
            error("Aborted by user!")
            return
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}-{InstanceType.ALGORITHM_STORE}"

    if name in running_server_names:
        container = client.containers.get(name)
        attach_logs(container, InstanceType.ALGORITHM_STORE)
    else:
        error(f"{Fore.RED}{name}{Style.RESET_ALL} is not running!")
