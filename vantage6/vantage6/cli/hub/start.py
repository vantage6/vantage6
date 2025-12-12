from pathlib import Path

import click

from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import execute_cli_start
from vantage6.cli.context.server import ServerContext
from vantage6.cli.globals import CLICommandName
from vantage6.cli.k8s_config import select_k8s_config


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--local-chart-dir",
    type=click.Path(exists=True),
    default=None,
    help="Local chart repository to use.",
)
@click_insert_context(type_=InstanceType.SERVER)
def cli_hub_start(
    ctx: ServerContext,
    context: str | None,
    namespace: str | None,
    local_chart_dir: Path | None,
) -> None:
    """
    Start a hub environment.
    """
    k8s_config = select_k8s_config(context=context, namespace=namespace)

    # First we need to start the keycloak service
    execute_cli_start(
        CLICommandName.AUTH,
        f"{ctx.name}-auth",
        k8s_config,
        local_chart_dir,
        system_folders=False,
        extra_args=["--wait-ready"],
    )

    # run the store. The store is started before the server so that the server can
    # couple to the store on startup.
    execute_cli_start(
        CLICommandName.ALGORITHM_STORE,
        f"{ctx.name}-store",
        k8s_config,
        local_chart_dir,
        system_folders=False,
    )

    # Then we need to start the server
    execute_cli_start(
        CLICommandName.SERVER,
        ctx.name,
        k8s_config,
        local_chart_dir,
        system_folders=False,
    )
