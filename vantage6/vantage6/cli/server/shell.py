import subprocess

import click
import docker
from colorama import Fore, Style

from vantage6.common import info, error, debug as debug_msg
from vantage6.common.docker.addons import check_docker_running
from vantage6.common.globals import APPNAME, InstanceType
from vantage6.cli.context.server import ServerContext
from vantage6.cli.common.decorator import click_insert_context


@click.command()
@click_insert_context(type_="server")
def cli_server_shell(ctx: ServerContext) -> None:
    """
    Run an iPython shell within a running server. This can be used to modify
    the database.

    NOTE: using the shell is no longer recommended as there is no validation on
    the changes that you make. It is better to use the Python client or a
    graphical user interface instead.
    """
    # will print an error if not
    check_docker_running()

    docker_client = docker.from_env()

    running_servers = docker_client.containers.list(
        filters={"label": f"{APPNAME}-type={InstanceType.SERVER}"}
    )

    if ctx.docker_container_name not in [s.name for s in running_servers]:
        error(f"Server {Fore.RED}{ctx.name}{Style.RESET_ALL} is not running?")
        return

    try:
        subprocess.run(
            [
                "docker",
                "exec",
                "-it",
                ctx.docker_container_name,
                "vserver-local",
                "shell",
                "-c",
                "/mnt/config.yaml",
            ]
        )
    except Exception as e:
        info("Failed to start subprocess...")
        debug_msg(e)
