import click

from vantage6.common import info
from vantage6.common.globals import InstanceType, Ports

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    start_port_forward,
)
from vantage6.cli.common.utils import (
    attach_logs,
    create_directory_if_not_exists,
    select_context_and_namespace,
)
from vantage6.cli.context.server import ServerContext
from vantage6.cli.globals import ChartName


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option("--ip", default=None, help="IP address to listen on")
@click.option(
    "-p", "--port", default=None, type=int, help="Port to listen on for the server"
)
@click.option(
    "--ui-port", default=None, type=int, help="Port to listen on for the User Interface"
)
@click.option(
    "--attach/--detach",
    default=False,
    help="Print server logs to the console after start",
)
@click_insert_context(type_=InstanceType.SERVER)
def cli_server_start(
    ctx: ServerContext,
    context: str,
    namespace: str,
    ip: str,
    port: int,
    ui_port: int,
    attach: bool,
) -> None:
    """
    Start the server.
    """
    info("Starting server...")
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    create_directory_if_not_exists(ctx.log_dir)

    helm_install(
        release_name=ctx.helm_release_name,
        chart_name=ChartName.SERVER,
        values_file=ctx.config_file,
        context=context,
        namespace=namespace,
    )

    # port forward for server
    info("Port forwarding for server")
    start_port_forward(
        service_name=f"{ctx.helm_release_name}-vantage6-server-service",
        service_port=ctx.config["server"].get("port", Ports.DEV_SERVER.value),
        port=port or ctx.config["server"].get("port", Ports.DEV_SERVER.value),
        ip=ip,
        context=context,
        namespace=namespace,
    )

    # port forward for UI
    info("Port forwarding for UI")
    start_port_forward(
        service_name=f"{ctx.helm_release_name}-vantage6-frontend-service",
        service_port=ctx.config["ui"].get("port", Ports.DEV_UI.value),
        port=ui_port or ctx.config["ui"].get("port", Ports.DEV_UI.value),
        ip=ip,
        context=context,
        namespace=namespace,
    )

    if attach:
        attach_logs("app=vantage6-server", "component=vantage6-server")
