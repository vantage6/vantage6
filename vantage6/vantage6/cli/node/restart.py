import subprocess
import click
import questionary as q
import docker

from vantage6.common import warning, error
from vantage6.common.docker.addons import check_docker_running
from vantage6.cli.common.utils import get_name_from_container_name
from vantage6.cli.node.stop import cli_node_stop
from vantage6.cli.node.common import find_running_node_names
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Search for configuration in system folders instead of " "user folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Search for configuration in the user folders instead of "
    "system folders. This is the default.",
)
@click.option("-i", "--image", default=None, help="Node Docker image to use")
@click.option(
    "--keep/--auto-remove",
    default=False,
    help="Keep node container after finishing. Useful for debugging",
)
@click.option(
    "--force-db-mount",
    is_flag=True,
    help="Always mount node databases; skip the check if they are existing files.",
)
@click.option(
    "--attach/--detach",
    default=False,
    help="Show node logs on the current console after starting the " "node",
)
@click.option(
    "--mount-src",
    default="",
    help="Override vantage6 source code in container with the source"
    " code in this path",
)
@click.option("--all", "all_nodes", flag_value=True, help="Stop all running nodes")
@click.option(
    "--force",
    "force",
    flag_value=True,
    help="Kill nodes instantly; don't wait for them to shut down",
)
@click.pass_context
def cli_node_restart(
    click_ctx: click.Context,
    name: str,
    system_folders: bool,
    image: str,
    keep: bool,
    mount_src: str,
    attach: bool,
    force_db_mount: bool,
    all_nodes: bool,
    force: bool,
) -> None:
    """Restart the node"""
    check_docker_running()
    client = docker.from_env()

    running_node_names = find_running_node_names(client)
    if not running_node_names:
        warning("No nodes are currently running. No action taken.")
        return

    if attach and all_nodes:
        error(
            "Cannot attach logs of all nodes at once. Please remove either the "
            "'--all' or '--attach' option."
        )
        return

    if all_nodes:
        names = [
            get_name_from_container_name(container_name)
            for container_name in running_node_names
        ]
    else:
        if not name:
            try:
                container_name = q.select(
                    "Select the node you wish to restart:", choices=running_node_names
                ).unsafe_ask()
            except KeyboardInterrupt:
                error("Aborted by user!")
                return
            names = [get_name_from_container_name(container_name)]
        else:
            names = [name]

    for node_name in names:
        click_ctx.invoke(
            cli_node_stop,
            name=node_name,
            system_folders=system_folders,
            all_nodes=False,
            force=force,
        )

        cmd = ["v6", "node", "start", "--name", node_name]
        if system_folders:
            cmd.append("--system")
        if image:
            cmd.extend(["--image", image])
        if keep:
            cmd.append("--keep")
        if mount_src:
            cmd.extend(["--mount-src", mount_src])
        if attach:
            cmd.append("--attach")
        if force_db_mount:
            cmd.append("--force-db-mount")
        subprocess.run(cmd, check=True)
