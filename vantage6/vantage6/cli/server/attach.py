import time
from threading import Thread

import click
import questionary as q
import docker

from colorama import Fore, Style

from vantage6.common import info, error
from vantage6.common.docker.addons import check_docker_running
from vantage6.common.globals import APPNAME, InstanceType

from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS
from vantage6.cli.common.utils import print_log_worker


@click.command()
@click.option("-n", "--name", default=None, help="configuration name")
@click.option("--system", "system_folders", flag_value=True)
@click.option(
    "--user", "system_folders", flag_value=False, default=DEFAULT_SERVER_SYSTEM_FOLDERS
)
def cli_server_attach(name: str, system_folders: bool) -> None:
    """
    Show the server logs in the current console.
    """
    check_docker_running()
    client = docker.from_env()

    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type={InstanceType.SERVER}"}
    )
    running_server_names = [node.name for node in running_servers]

    if not name:
        try:
            name = q.select(
                "Select the server you wish to attach:", choices=running_server_names
            ).unsafe_ask()
        except KeyboardInterrupt:
            error("Aborted by user!")
            return
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}-{InstanceType.SERVER}"

    if name in running_server_names:
        container = client.containers.get(name)
        logs = container.attach(stream=True, logs=True, stdout=True)
        Thread(target=print_log_worker, args=(logs,), daemon=True).start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                info("Closing log file. Keyboard Interrupt.")
                info(
                    "Note that your server is still running! Shut it down "
                    f"with {Fore.RED}v6 server stop{Style.RESET_ALL}"
                )
                exit(0)
    else:
        error(f"{Fore.RED}{name}{Style.RESET_ALL} was not running!?")
