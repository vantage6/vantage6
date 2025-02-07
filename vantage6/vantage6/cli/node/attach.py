import time
from threading import Thread
import click
import questionary as q
import docker

from colorama import Fore, Style

from vantage6.common import warning, error, info
from vantage6.common.globals import APPNAME
from vantage6.common.docker.addons import check_docker_running

from vantage6.cli.common.utils import print_log_worker
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
from vantage6.cli.node.common import find_running_node_names


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Search for configuration in system folders rather than " "user folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Search for configuration in user folders rather than "
    "system folders. This is the default",
)
def cli_node_attach(name: str, system_folders: bool) -> None:
    """
    Show the node logs in the current console.
    """
    check_docker_running()
    client = docker.from_env()

    running_node_names = find_running_node_names(client)

    if not running_node_names:
        warning("No nodes are currently running. Cannot show any logs!")
        return

    if not name:
        try:
            name = q.select(
                "Select the node you wish to attach:", choices=running_node_names
            ).unsafe_ask()
        except KeyboardInterrupt:
            error("Aborted by user!")
            return
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}"

    if name in running_node_names:
        container = client.containers.get(name)
        logs = container.attach(stream=True, logs=True)
        Thread(target=print_log_worker, args=(logs,), daemon=True).start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                info("Closing log file. Keyboard Interrupt.")
                info(
                    "Note that your node is still running! Shut it down with "
                    f"'{Fore.RED}v6 node stop{Style.RESET_ALL}'"
                )
                exit(0)
    else:
        error(f"{Fore.RED}{name}{Style.RESET_ALL} was not running!?")
