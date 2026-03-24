import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.auth.install import check_and_install_keycloak_operator
from vantage6.cli.auth.k8s_utils import wait_for_keycloak_ready
from vantage6.cli.common.attach import attach_logs
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    prestart_checks,
)
from vantage6.cli.context.auth import AuthContext
from vantage6.cli.globals import ChartName, InfraComponentName
from vantage6.cli.k8s_config import select_k8s_config


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--attach/--detach",
    default=False,
    help="Print auth logs to the console after start",
)
@click.option("--local-chart-dir", default=None, help="Local chart directory to use")
@click.option("--chart-version", default=None, help="Chart version to use")
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click.option("--wait-ready/--no-wait-ready", "wait_ready", default=False)
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
    attach: bool,
    local_chart_dir: str,
    chart_version: str | None,
    wait_ready: bool,
) -> None:
    """
    Start the auth service.
    """
    info("Starting authentication service...")

    prestart_checks(ctx, InstanceType.AUTH, name, system_folders)

    k8s_config = select_k8s_config(context=context, namespace=namespace)

    check_and_install_keycloak_operator(k8s_config)

    # TODO: re-enable when we save the auth logs
    # create_directory_if_not_exists(ctx.log_dir)

    info("Starting auth service. This may take a few minutes...")
    helm_install(
        release_name=ctx.helm_release_name,
        chart_name=ChartName.AUTH,
        values_file=ctx.config_file,
        k8s_config=k8s_config,
        local_chart_dir=local_chart_dir,
        chart_version=chart_version,
    )

    # Note that we also wait in case of attach - if not ready, we cannot attach
    if wait_ready or attach:
        wait_for_keycloak_ready(ctx.helm_release_name, k8s_config)

    if attach:
        attach_logs(
            name,
            instance_type=InstanceType.AUTH,
            infra_component=InfraComponentName.AUTH,
            system_folders=system_folders,
            k8s_config=k8s_config,
            is_sandbox=ctx.is_sandbox,
        )
