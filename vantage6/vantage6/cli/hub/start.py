from pathlib import Path

import click

from vantage6.common import info, warning
from vantage6.common.globals import InstanceType

from vantage6.cli.auth.install import check_and_install_keycloak_operator
from vantage6.cli.auth.k8s_utils import wait_for_keycloak_ready
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.k8s_utils import wait_for_pod_ready
from vantage6.cli.common.start import helm_install, prestart_checks
from vantage6.cli.context.hub import HubContext
from vantage6.cli.globals import ChartName
from vantage6.cli.hub.install import (
    cert_manager_seems_installed,
    check_and_install_cert_manager_crds,
)
from vantage6.cli.hub.utils.ingress import ensure_ingress_controller
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
@click.option(
    "--auto-install-ingress/--no-auto-install-ingress",
    "auto_install_ingress",
    default=True,
    help=(
        "Automatically install an NGINX ingress controller when hub ingress is "
        "enabled and no suitable controller is detected."
    ),
)
@click.option(
    "--azure/--no-azure",
    "azure",
    default=False,
    help="Optimize ingress controller installation for Azure load balancers.",
)
@click.option(
    "--ingress-class-name",
    default=None,
    help=(
        "IngressClass name to use for hub ingresses. "
        "Defaults to the value from hubIngress.ingressClassName in the "
        "configuration, or 'nginx' if not set."
    ),
)
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
    auto_install_ingress: bool,
    ingress_class_name: str | None,
    azure: bool,
) -> None:
    """
    Start a hub environment.
    """
    info("Starting hub...")

    prestart_checks(ctx, InstanceType.HUB, name, system_folders)

    k8s_config = select_k8s_config(context=context, namespace=namespace)

    # Before starting the hub, ensure required operators / CRDs are installed.
    hub_ingress = ctx.config.get("hubIngress", {})
    tls_cfg = hub_ingress.get("tls", {})

    # 1) cert-manager CRDs are needed for Certificate resources used by the hub
    #    chart, but only when ingress is enabled and configured to use
    #    cert-manager.
    if hub_ingress.get("enabled") and tls_cfg.get("mode") == "cert-manager":
        check_and_install_cert_manager_crds(k8s_config)
        if not cert_manager_seems_installed(k8s_config):
            warning(
                "⚠️  hubIngress.tls.mode is set to 'cert-manager', but cert-manager "
                "does not appear to be installed. No automatic installation will "
                "be attempted; please install and configure cert-manager (or "
                "switch hubIngress.tls.mode to 'existingSecret')."
            )

    # 2) Ensure an ingress controller is available when hub ingress is enabled.
    if hub_ingress.get("enabled"):
        # Determine which ingress class to use: CLI flag, then config, then
        # sensible default.
        desired_ingress_class = (
            ingress_class_name or hub_ingress.get("ingressClassName") or "nginx"
        )
        ensure_ingress_controller(
            k8s_config,
            ingress_class_name=desired_ingress_class,
            auto_install=auto_install_ingress,
            azure=azure,
        )

    # 3) Keycloak operator (and its CRDs) are needed for the auth subchart.
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
