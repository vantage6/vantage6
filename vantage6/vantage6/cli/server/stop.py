import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.stop import helm_uninstall, stop_port_forward
from vantage6.cli.config import CliConfig
from vantage6.cli.context.server import ServerContext


@click.command()
# add context and namespace options
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click_insert_context(type_=InstanceType.SERVER)
def cli_server_stop(
    ctx: ServerContext,
    context: str,
    namespace: str,
):
    """
    Stop an running server.
    """
    cli_config = CliConfig()

    context, namespace = cli_config.compare_changes_config(
        context=context,
        namespace=namespace,
    )

    # uninstall the helm release
    info("Stopping server...")
    release_name = f"{ctx.name}-{ctx.instance_type}"
    helm_uninstall(
        release_name=release_name,
        context=context,
        namespace=namespace,
    )

    # stop the port forwarding for server and UI
    stop_port_forward(
        service_name=f"{release_name}-vantage6-server-service",
    )

    stop_port_forward(
        service_name=f"{release_name}-vantage6-frontend-service",
    )

    info("Server stopped successfully.")
