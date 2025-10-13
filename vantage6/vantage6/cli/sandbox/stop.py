import subprocess

import click

from vantage6.common import error
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import (
    find_running_service_names,
    select_context_and_namespace,
    select_running_service,
)
from vantage6.cli.context import get_context
from vantage6.cli.context.node import NodeContext
from vantage6.cli.server.stop import cli_server_stop


@click.command()
@click.option("-n", "--name", default=None, help="Name of the configuration.")
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.pass_context
def cli_sandbox_stop(
    click_ctx: click.Context,
    name: str | None,
    context: str | None,
    namespace: str | None,
) -> None:
    """
    Stop a sandbox environment.
    """
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    running_services = find_running_service_names(
        instance_type=InstanceType.SERVER,
        only_system_folders=False,
        only_user_folders=False,
        context=context,
        namespace=namespace,
        sandbox=True,
    )

    if not running_services:
        error("No running sandbox services found.")
        return

    if not name:
        selected_service = select_running_service(running_services, InstanceType.SERVER)
        name = selected_service.split("-")[-3]
    else:
        ctx = get_context(InstanceType.SERVER, name, False, is_sandbox=True)
        name = ctx.name

    # stop the sandbox nodes
    nodes_user_folder, _ = NodeContext.available_configurations(False, is_sandbox=True)
    for node in nodes_user_folder:
        if node.name.startswith(f"{name}-node-"):
            cmd = [
                "v6",
                "node",
                "stop",
                "--name",
                node.name,
                "--sandbox",
                "--context",
                context,
                "--namespace",
                namespace,
            ]
            subprocess.run(cmd, check=True)

    # # Stop all server services
    click_ctx.invoke(
        cli_server_stop,
        name=name,
        context=context,
        namespace=namespace,
        system_folders=False,
        all_servers=False,
        is_sandbox=True,
    )

    # TODO: stop the auth service
    cmd = [
        "v6",
        "auth",
        "stop",
        "--name",
        f"{name}-auth.sandbox",
        "--sandbox",
    ]
    subprocess.run(cmd, check=True)

    # stop the algorithm store
    cmd = [
        "v6",
        "algorithm-store",
        "stop",
        "--name",
        f"{name}-store.sandbox",
        "--sandbox",
    ]
    subprocess.run(cmd, check=True)
