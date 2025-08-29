import click

from vantage6.common import info
from vantage6.common.globals import (
    InstanceType,
    Ports,
)

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    prestart_checks,
    start_port_forward,
)
from vantage6.cli.common.utils import (
    attach_logs,
    create_directory_if_not_exists,
)
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.cli.globals import ChartName


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option("--ip", default=None, help="IP address to listen on")
@click.option("-p", "--port", default=None, type=int, help="Port to listen on")
@click.option(
    "--attach/--detach",
    default=False,
    help="Print server logs to the console after start",
)
@click_insert_context(
    InstanceType.ALGORITHM_STORE, include_name=True, include_system_folders=True
)
def cli_algo_store_start(
    ctx: AlgorithmStoreContext,
    name: str,
    system_folders: bool,
    context: str,
    namespace: str,
    ip: str,
    port: int,
    attach: bool,
) -> None:
    """
    Start the algorithm store.
    """
    info("Starting algorithm store...")

    prestart_checks(
        ctx, InstanceType.ALGORITHM_STORE, name, system_folders, context, namespace
    )

    create_directory_if_not_exists(ctx.log_dir)

    helm_install(
        release_name=ctx.helm_release_name,
        chart_name=ChartName.ALGORITHM_STORE,
        values_file=ctx.config_file,
        context=context,
        namespace=namespace,
    )

    info("Port forwarding for algorithm store")
    start_port_forward(
        service_name=f"{ctx.helm_release_name}-store-service",
        service_port=ctx.config["store"].get("port", Ports.DEV_ALGO_STORE.value),
        port=port or ctx.config["store"].get("port", Ports.DEV_ALGO_STORE.value),
        ip=ip,
        context=context,
        namespace=namespace,
    )

    if attach:
        attach_logs("app=store", "component=store-server")
