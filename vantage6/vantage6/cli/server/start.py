import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    start_port_forward,
)
from vantage6.cli.common.utils import attach_logs
from vantage6.cli.config import CliConfig
from vantage6.cli.context.server import ServerContext


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
    cli_config = CliConfig()

    context, namespace = cli_config.compare_changes_config(
        context=context,
        namespace=namespace,
    )

    # check that log directory exists - or create it
    ctx.log_dir.mkdir(parents=True, exist_ok=True)

    release_name = f"{ctx.name}-{ctx.instance_type}"
    helm_install(
        release_name=release_name,
        chart_name="server",
        values_file=ctx.config_file,
        context=context,
        namespace=namespace,
    )

    # port forward for server
    info("Port forwarding for server")
    start_port_forward(
        service_name=f"{release_name}-vantage6-server-service",
        service_port=ctx.config["server"].get("port", 7601),
        port=port or ctx.config["server"].get("port", 7601),
        ip=ip,
        context=context,
        namespace=namespace,
    )

    # port forward for UI
    info("Port forwarding for UI")
    start_port_forward(
        service_name=f"{release_name}-vantage6-frontend-service",
        service_port=ctx.config["ui"].get("port", 7600),
        port=ui_port or ctx.config["ui"].get("port", 7600),
        ip=ip,
        context=context,
        namespace=namespace,
    )

    if attach:
        attach_logs("app=vantage6-server", "component=vantage6-server")
