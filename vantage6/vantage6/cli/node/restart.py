import subprocess
import time

import click
import questionary as q

from vantage6.common import error, info, warning
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import (
    find_running_service_names,
    get_config_name_from_service_name,
    select_context_and_namespace,
)
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
from vantage6.cli.node.stop import cli_node_stop


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Search for configuration in system folders instead of user folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Search for configuration in the user folders instead of "
    "system folders. This is the default.",
)
@click.option(
    "--attach/--detach",
    default=False,
    help="Show node logs on the current console after starting the node",
)
@click.option("--all", "all_nodes", flag_value=True, help="Stop all running nodes")
@click.option("--sandbox", "is_sandbox", flag_value=True, help="Restart a sandbox node")
@click.pass_context
def cli_node_restart(
    click_ctx: click.Context,
    name: str,
    context: str,
    namespace: str,
    system_folders: bool,
    attach: bool,
    all_nodes: bool,
    is_sandbox: bool,
) -> None:
    """Restart the node"""
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    running_node_names = find_running_service_names(
        instance_type=InstanceType.NODE,
        only_system_folders=system_folders,
        only_user_folders=not system_folders,
        context=context,
        namespace=namespace,
    )
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
            get_config_name_from_service_name(container_name)
            for container_name in running_node_names
        ]
    else:
        if not name:
            try:
                helm_name = q.select(
                    "Select the node you wish to restart:", choices=running_node_names
                ).unsafe_ask()
            except KeyboardInterrupt:
                error("Aborted by user!")
                return
            names = [get_config_name_from_service_name(helm_name)]
        else:
            names = [name]

    for node_name in names:
        click_ctx.invoke(
            cli_node_stop,
            name=node_name,
            system_folders=system_folders,
            context=context,
            namespace=namespace,
            all_nodes=False,
            is_sandbox=is_sandbox,
        )

        # TODO #2334 This is poor. We give this time for k8s to delete the volumes etc. If we
        # start the node again too early, it will fail because it cannot create new
        # volumes while the old ones are still being delete. We should detect when the
        # volumes are deleted and then start the node immediately.
        info("Waiting 30 seconds for the node to stop entirely...")
        time.sleep(30)

        cmd = [
            "v6",
            "node",
            "start",
            "--name",
            node_name,
            "--context",
            context,
            "--namespace",
            namespace,
        ]
        if system_folders:
            cmd.append("--system")
        if attach:
            cmd.append("--attach")
        if is_sandbox:
            cmd.append("--sandbox")
        subprocess.run(cmd, check=True)
