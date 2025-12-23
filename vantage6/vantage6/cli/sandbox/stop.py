import click

from vantage6.common import error
from vantage6.common.globals import InstanceType

from vantage6.cli.common.stop import execute_cli_stop
from vantage6.cli.common.utils import (
    find_running_service_names,
    get_config_name_from_helm_release_name,
    select_running_service,
)
from vantage6.cli.context import get_context
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import CLICommandName
from vantage6.cli.k8s_config import select_k8s_config


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
    k8s_config = select_k8s_config(context=context, namespace=namespace)

    running_services = find_running_service_names(
        instance_type=InstanceType.HQ,
        only_system_folders=False,
        only_user_folders=False,
        k8s_config=k8s_config,
    )

    if not running_services:
        error("No running sandbox services found.")
        return

    if not name:
        selected_service = select_running_service(running_services, InstanceType.HQ)
        name = get_config_name_from_helm_release_name(selected_service)
    else:
        ctx = get_context(InstanceType.HQ, name, False, is_sandbox=True)
        name = ctx.name

    # stop the sandbox nodes
    nodes_user_folder, _ = NodeContext.available_configurations(False, is_sandbox=True)
    for node in nodes_user_folder:
        if node.name.startswith(f"{name}-node-"):
            execute_cli_stop(
                command_name=CLICommandName.NODE,
                name=node.name,
                k8s_config=k8s_config,
                system_folders=False,
                is_sandbox=True,
            )

    execute_cli_stop(
        command_name=CLICommandName.AUTH,
        name=f"{name}-auth.sandbox",
        k8s_config=k8s_config,
        system_folders=False,
        is_sandbox=True,
    )
    execute_cli_stop(
        command_name=CLICommandName.ALGORITHM_STORE,
        name=f"{name}-store.sandbox",
        k8s_config=k8s_config,
        system_folders=False,
        is_sandbox=True,
    )
    execute_cli_stop(
        command_name=CLICommandName.HQ,
        name=name,
        k8s_config=k8s_config,
        system_folders=False,
        is_sandbox=True,
    )
