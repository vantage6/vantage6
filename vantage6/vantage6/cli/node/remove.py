import click
import questionary as q
import docker
import os.path
import itertools

from pathlib import Path
from shutil import rmtree

from vantage6.common import (
    error,
    info,
    debug,
)
from vantage6.common.globals import APPNAME


from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
from vantage6.cli.utils import check_if_docker_daemon_is_running, remove_file
from vantage6.cli.node.common import select_node, find_running_node_names

# TODO v5+ remove this - just a dummy to prevent import issues from v4 CLI
# from vantage6.common.globals import VPN_CONFIG_FILE
VPN_CONFIG_FILE = "vpn.conf"


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
@click.option(
    "-f", "--force", type=bool, flag_value=True, help="Don't ask for confirmation"
)
def cli_node_remove(name: str, system_folders: bool, force: bool) -> None:
    """
    Delete a node permanently.

    Remove the configuration file, log file, and docker volumes attached to
    the node.
    """
    # select configuration name if none supplied
    name = select_node(name, system_folders)

    client = docker.from_env()
    check_if_docker_daemon_is_running(client)

    # check if node is still running, otherwise don't allow deleting it
    running_node_names = find_running_node_names(client)

    post_fix = "system" if system_folders else "user"
    node_container_name = f"{APPNAME}-{name}-{post_fix}"
    if node_container_name in running_node_names:
        error(
            f"Node {name} is still running! Please stop the node before " "deleting it."
        )
        exit(1)

    if not force:
        if not q.confirm(
            "This node will be deleted permanently including its "
            "configuration. Are you sure?",
            default=False,
        ).ask():
            info("Node will not be deleted")
            exit(0)

    # create node context
    ctx = NodeContext(name, system_folders=system_folders)

    # remove the docker volume and any temporary volumes
    debug("Deleting docker volumes")
    volumes = client.volumes.list()
    for vol in volumes:
        if vol.name.startswith(ctx.docker_volume_name):  # includes tmp volumes
            info(f"Deleting docker volume {vol.name}")
            vol.remove()
        # remove docker vpn volume
        if vol.name == ctx.docker_vpn_volume_name:
            info(f"Deleting VPN docker volume {vol.name}")
            vol.remove()

    # remove the VPN configuration file
    vpn_config_file = os.path.join(ctx.data_dir, "vpn", VPN_CONFIG_FILE)
    remove_file(vpn_config_file, "VPN configuration")

    # remove the config file
    remove_file(ctx.config_file, "configuration")

    # remove the log file. As this process opens the log file above, the log
    # handlers need to be closed before deleting
    log_dir = Path(ctx.log_file.parent)
    info(f"Removing log file {log_dir}")
    for handler in itertools.chain(ctx.log.handlers, ctx.log.root.handlers):
        handler.close()
    # remove the whole folder with all the log files
    rmtree(log_dir)

    # remove the folder: if it hasn't been started yet this won't exist...
    if Path.exists(ctx.config_dir / name):
        rmtree(ctx.config_dir / name)
