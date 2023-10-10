import click
import questionary as q
import docker

from vantage6.common import error
from vantage6.common.docker.addons import check_docker_running
from vantage6.common.globals import APPNAME
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS
from vantage6.cli import __version__


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=DEFAULT_SERVER_SYSTEM_FOLDERS)
def cli_server_version(name: str, system_folders: bool) -> None:
    """
    Print the version of the vantage6 server.
    """
    check_docker_running()
    client = docker.from_env()

    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type=server"})
    running_server_names = [server.name for server in running_servers]

    if not name:
        if not running_server_names:
            error("No servers are running! You can only check the version for "
                  "servers that are running")
            exit(1)
        name = q.select("Select the server you wish to inspect:",
                        choices=running_server_names).ask()
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}"

    if name in running_server_names:
        container = client.containers.get(name)
        version = container.exec_run(cmd='vserver-local version',
                                     stdout=True)
        click.echo({"server": version.output.decode('utf-8'),
                    "cli": __version__})
    else:
        error(f"Server {name} is not running! Cannot provide version...")
