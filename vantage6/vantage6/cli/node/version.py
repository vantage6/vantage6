import click
import questionary as q
import docker

from vantage6.common import error
from vantage6.common.globals import APPNAME
from vantage6.common.docker.addons import check_docker_running
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
from vantage6.cli import __version__
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
def cli_node_version(name: str, system_folders: bool) -> None:
    """
    Returns current version of a vantage6 node.
    """
    check_docker_running()
    client = docker.from_env()

    running_node_names = find_running_node_names(client)

    if not name:
        if not running_node_names:
            error(
                "No nodes are running! You can only check the version for "
                "nodes that are running"
            )
            exit(1)
        try:
            name = q.select(
                "Select the node you wish to inspect:", choices=running_node_names
            ).unsafe_ask()
        except KeyboardInterrupt:
            error("Aborted by user!")
            return
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}"

    if name in running_node_names:
        container = client.containers.get(name)
        version = container.exec_run(cmd="vnode-local version", stdout=True)
        click.echo({"node": version.output.decode("utf-8"), "cli": __version__})
    else:
        error(f"Node {name} is not running! Cannot provide version...")
