import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.attach import attach_logs
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    prestart_checks,
)
from vantage6.cli.common.utils import create_directory_if_not_exists
from vantage6.cli.context.hq import HQContext
from vantage6.cli.globals import ChartName, InfraComponentName
from vantage6.cli.k8s_config import select_k8s_config


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--attach/--detach",
    default=False,
    help="Print HQ logs to the console after start",
)
@click.option("--local-chart-dir", default=None, help="Local chart directory to use")
@click.option("--chart-version", default=None, help="Chart version to use")
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(
    type_=InstanceType.HQ,
    include_name=True,
    include_system_folders=True,
    sandbox_param="sandbox",
)
def cli_hq_start(
    ctx: HQContext,
    name: str,
    system_folders: bool,
    context: str,
    namespace: str,
    attach: bool,
    local_chart_dir: str | None,
    chart_version: str | None,
) -> None:
    """
    Start an instance of vantage6 HQ.
    """
    info("Starting HQ...")
    prestart_checks(ctx, InstanceType.HQ, name, system_folders)

    k8s_config = select_k8s_config(context=context, namespace=namespace)

    create_directory_if_not_exists(ctx.log_dir)

    helm_install(
        release_name=ctx.helm_release_name,
        chart_name=ChartName.HQ,
        values_file=ctx.config_file,
        k8s_config=k8s_config,
        local_chart_dir=local_chart_dir,
        chart_version=chart_version,
    )

    if attach:
        attach_logs(
            name,
            instance_type=InstanceType.HQ,
            infra_component=InfraComponentName.HQ,
            system_folders=system_folders,
            k8s_config=k8s_config,
            is_sandbox=ctx.is_sandbox,
        )
