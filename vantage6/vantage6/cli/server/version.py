import click
import docker

from vantage6.common import error
from vantage6.common.docker.addons import check_docker_running
from vantage6.common.globals import InstanceType

from vantage6.cli import __version__
from vantage6.cli.common.utils import get_running_servers, get_server_name
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--system", "system_folders", flag_value=True)
@click.option(
    "--user", "system_folders", flag_value=False, default=DEFAULT_SERVER_SYSTEM_FOLDERS
)
def cli_server_version(name: str, system_folders: bool) -> None:
    """
    Print the version of the vantage6 server.
    """
    check_docker_running()
    client = docker.from_env()

    running_server_names = get_running_servers(client, InstanceType.SERVER)

    name = get_server_name(
        name, system_folders, running_server_names, InstanceType.SERVER
    )

    if name in running_server_names:
        container = client.containers.get(name)
        version = container.exec_run(cmd="vserver-local version", stdout=True)
        click.echo({"server": version.output.decode("utf-8"), "cli": __version__})
    else:
        error(f"Server {name} is not running! Cannot provide version...")
