import click

from vantage6.common import info
from vantage6.common.globals import InstanceType, Ports

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    prestart_checks,
    start_port_forward,
)
from vantage6.cli.common.utils import (
    attach_logs,
)
from vantage6.cli.context.auth import AuthContext
from vantage6.cli.globals import ChartName


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option("--ip", default=None, help="IP address to listen on")
@click.option(
    "-p",
    "--port",
    default=None,
    type=int,
    help="Port to listen on for the auth service",
)
@click.option(
    "--attach/--detach",
    default=False,
    help="Print server logs to the console after start",
)
@click_insert_context(
    type_=InstanceType.AUTH, include_name=True, include_system_folders=True
)
def cli_auth_start(
    ctx: AuthContext,
    name: str,
    system_folders: bool,
    context: str,
    namespace: str,
    ip: str,
    port: int,
    attach: bool,
) -> None:
    """
    Start the auth service.
    """
    info("Starting authentication service...")

    prestart_checks(ctx, InstanceType.AUTH, name, system_folders, context, namespace)

    # TODO: re-enable when we save the auth logs
    # create_directory_if_not_exists(ctx.log_dir)

    helm_install(
        release_name=ctx.helm_release_name,
        chart_name=ChartName.AUTH,
        values_file=ctx.config_file,
        context=context,
        namespace=namespace,
    )

    # port forward for auth service
    info("Port forwarding for auth service")
    start_port_forward(
        service_name=f"{ctx.helm_release_name}-keycloak",
        service_port=Ports.HTTP.value,
        port=port or Ports.DEV_AUTH.value,
        ip=ip,
        context=context,
        namespace=namespace,
    )

    if attach:
        attach_logs(
            f"app.kubernetes.io/instance={ctx.helm_release_name}",
        )
