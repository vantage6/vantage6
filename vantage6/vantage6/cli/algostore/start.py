import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.attach import attach_logs
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    prestart_checks,
)
from vantage6.cli.common.utils import (
    create_directory_if_not_exists,
    select_context_and_namespace,
)
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.cli.globals import ChartName, InfraComponentName


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--attach/--detach",
    default=False,
    help="Print server logs to the console after start",
)
@click.option("--local-chart-dir", default=None, help="Local chart directory to use")
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(
    InstanceType.ALGORITHM_STORE,
    include_name=True,
    include_system_folders=True,
    sandbox_param="sandbox",
)
def cli_algo_store_start(
    ctx: AlgorithmStoreContext,
    name: str,
    system_folders: bool,
    context: str,
    namespace: str,
    attach: bool,
    local_chart_dir: str,
) -> None:
    """
    Start the algorithm store.
    """
    info("Starting algorithm store...")

    prestart_checks(ctx, InstanceType.ALGORITHM_STORE, name, system_folders)

    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    create_directory_if_not_exists(ctx.log_dir)

    helm_install(
        release_name=ctx.helm_release_name,
        chart_name=ChartName.ALGORITHM_STORE,
        values_file=ctx.config_file,
        context=context,
        namespace=namespace,
        local_chart_dir=local_chart_dir,
    )

    if attach:
        attach_logs(
            name,
            instance_type=InstanceType.ALGORITHM_STORE,
            infra_component=InfraComponentName.ALGORITHM_STORE,
            system_folders=system_folders,
            context=context,
            namespace=namespace,
            is_sandbox=ctx.is_sandbox,
        )
