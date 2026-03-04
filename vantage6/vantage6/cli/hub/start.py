from pathlib import Path

import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.auth.install import check_and_install_keycloak_operator
from vantage6.cli.auth.k8s_utils import wait_for_keycloak_ready
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.k8s_utils import wait_for_pod_ready
from vantage6.cli.common.start import helm_install, prestart_checks
from vantage6.cli.context.hub import HubContext
from vantage6.cli.globals import ChartName
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
@click.option("--chart-version", default=None, help="Chart version to use")
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click.option("--wait-ready/--no-wait-ready", "wait_ready", default=True)
@click_insert_context(
    type_=InstanceType.HUB,
    include_name=True,
    include_system_folders=True,
    sandbox_param="sandbox",
)
def cli_hub_start(
    ctx: HubContext,
    name: str,
    system_folders: bool,
    context: str | None,
    namespace: str | None,
    local_chart_dir: Path | None,
    chart_version: str | None,
    wait_ready: bool,
) -> None:
    """
    Start a hub environment.
    """
    info("Starting hub...")

    prestart_checks(ctx, InstanceType.HUB, name, system_folders)

    k8s_config = select_k8s_config(context=context, namespace=namespace)

    # before starting the hub, we need to install the keycloak operator (if not already
    # installed)
    check_and_install_keycloak_operator(k8s_config)

    helm_install(
        release_name=ctx.helm_release_name,
        chart_name=ChartName.HUB,
        values_file=ctx.config_file,
        k8s_config=k8s_config,
        local_chart_dir=local_chart_dir,
        chart_version=chart_version,
    )

    if wait_ready:
        info("Waiting for hub services to become ready (auth, hq, store)...")
        wait_for_keycloak_ready(ctx.helm_release_name, k8s_config)
        wait_for_pod_ready(
            selector=(
                f"app=vantage6-store,release={ctx.helm_release_name},component=store"
            ),
            description="Store",
            k8s_config=k8s_config,
        )
        wait_for_pod_ready(
            selector=(
                f"app=vantage6-hq,release={ctx.helm_release_name},component=vantage6-hq"
            ),
            description="HQ",
            k8s_config=k8s_config,
        )
        info("Hub services are ready.")
    else:
        info("Hub services have been started.")
        info("You may need to wait for the services to become ready.")
