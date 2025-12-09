import subprocess
import time

import click

from vantage6.common import info, warning
from vantage6.common.globals import InstanceType

from vantage6.cli.auth.install import check_and_install_keycloak_operator
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    prestart_checks,
)
from vantage6.cli.context.auth import AuthContext
from vantage6.cli.globals import ChartName
from vantage6.cli.k8s_config import select_k8s_config


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--attach/--detach",
    default=False,
    help="Print server logs to the console after start",
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

    if wait_ready:
        _wait_for_keycloak_ready(ctx.helm_release_name, k8s_config)

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


def _kubectl(args: list[str], k8s_config) -> None:
    """
    Run a kubectl command with optional context/namespace from k8s_config.
    """
    cmd = ["kubectl"] + args
    if k8s_config.context:
        cmd.extend(["--context", k8s_config.context])
    if k8s_config.namespace:
        cmd.extend(["--namespace", k8s_config.namespace])
    return subprocess.run(
        cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def _wait_for_keycloak_ready(release_name: str, k8s_config) -> None:
    """
    Ensure Keycloak pod is ready and realm import job finished.
    """
    selector = f"app.kubernetes.io/instance={release_name}-kc"
    info("Waiting for Keycloak pod to be created...")
    while True:
        result = _kubectl(["get", "pod", "-l", selector], k8s_config)
        if result.returncode == 0:
            break
        else:
            time.sleep(1)
    info("Keycloak pod was created, waiting for it to be ready...")
    _kubectl(
        ["wait", "--for=condition=ready", "pod", "-l", selector, "--timeout", "300s"],
        k8s_config,
    )
