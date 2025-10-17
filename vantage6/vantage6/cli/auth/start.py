import click

from vantage6.common import info, warning
from vantage6.common.globals import InstanceType, Ports

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    prestart_checks,
    start_port_forward,
)
from vantage6.cli.common.utils import select_context_and_namespace
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
@click.option("--local-chart-dir", default=None, help="Local chart directory to use")
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(
    type_=InstanceType.AUTH,
    include_name=True,
    include_system_folders=True,
    sandbox_param="sandbox",
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
    local_chart_dir: str,
) -> None:
    """
    Start the auth service.
    """
    info("Starting authentication service...")

    prestart_checks(ctx, InstanceType.AUTH, name, system_folders)

    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    # TODO: re-enable when we save the auth logs
    # create_directory_if_not_exists(ctx.log_dir)

    info("Starting auth service. This may take a few minutes...")
    helm_install(
        release_name=ctx.helm_release_name,
        chart_name=ChartName.AUTH,
        values_file=ctx.config_file,
        context=context,
        namespace=namespace,
        local_chart_dir=local_chart_dir,
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
        warning("Attaching to auth logs is not supported yet.")
        # attach_logs(
        #     name,
        #     instance_type=InstanceType.AUTH,
        #     infra_component=InfraComponentName.AUTH,
        #     system_folders=system_folders,
        #     context=context,
        #     namespace=namespace,
        #     is_sandbox=ctx.is_sandbox,
        # )
