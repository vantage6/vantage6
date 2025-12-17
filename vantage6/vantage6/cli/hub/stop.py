import click

from vantage6.common import error
from vantage6.common.globals import InstanceType

from vantage6.cli.common.stop import execute_cli_stop
from vantage6.cli.common.utils import (
    find_running_service_names,
    select_running_service,
)
from vantage6.cli.context import get_context
from vantage6.cli.globals import CLICommandName
from vantage6.cli.k8s_config import select_k8s_config


@click.command()
@click.option("-n", "--name", default=None, help="Name of the configuration.")
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
def cli_hub_stop(
    name: str | None,
    context: str | None,
    namespace: str | None,
) -> None:
    """
    Stop a hub.
    """
    k8s_config = select_k8s_config(context=context, namespace=namespace)

    running_services = find_running_service_names(
        instance_type=InstanceType.HQ,
        only_system_folders=False,
        only_user_folders=False,
        k8s_config=k8s_config,
    )

    if not running_services:
        error("No running services found.")
        return

    if not name:
        selected_service = select_running_service(running_services, InstanceType.HQ)
        name = "-".join(selected_service.split("-")[1:-2])
    else:
        ctx = get_context(InstanceType.HQ, name, False)
        name = ctx.name

    execute_cli_stop(CLICommandName.AUTH, f"{name}-auth", k8s_config, False)
    execute_cli_stop(CLICommandName.ALGORITHM_STORE, f"{name}-store", k8s_config, False)
    execute_cli_stop(CLICommandName.SERVER, name, k8s_config, False)
