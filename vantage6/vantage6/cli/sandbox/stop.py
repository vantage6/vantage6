import subprocess

import click

from vantage6.common import error

# from vantage6.cli.common.decorator import click_insert_context
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import (
    find_running_service_names,
    select_context_and_namespace,
    select_running_service,
)
from vantage6.cli.context import get_context

# from vantage6.cli.node.stop import cli_node_stop
# from vantage6.cli.algostore.stop import cli_algo_store_stop
# from vantage6.cli.common.stop import helm_uninstall
# from vantage6.cli.context.server import ServerContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.node.stop import cli_node_stop

# from vantage6.cli.context.node import NodeContext
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

    # find all related nodes
    nodes = NodeContext.available_configurations(False, is_sandbox=True)
    for node in nodes[0]:
        if node.name.startswith(f"{name}-node-"):
            ctx = get_context(InstanceType.NODE, node.name, False, is_sandbox=True)
            click_ctx.invoke(
                cli_node_stop,
                name=ctx.name,
                context=context,
                namespace=namespace,
                system_folders=False,
                all_nodes=False,
                is_sandbox=True,
            )

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

    # # stop the nodes
    # configs, _ = NodeContext.available_configurations(False)
    # node_names = [
    #     config.name for config in configs if config.name.startswith(f"{ctx.name}_node_")
    # ]
    # for name in node_names:
    #     click_ctx.invoke(
    #         cli_node_stop, name=name, system_folders=False, all_nodes=False, force=False
    #     )
