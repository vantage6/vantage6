import subprocess
import time
from pathlib import Path

import click

from vantage6.common import info, warning
from vantage6.common.globals import InstanceType

from vantage6.cli.auth.install import check_and_install_keycloak_operator
from vantage6.cli.common.decorator import click_insert_context
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

    info("Waiting for hub services to become ready (auth, hq, store)...")
    _wait_for_keycloak_ready(ctx.helm_release_name, k8s_config)
    _wait_for_component_ready(
        "Store",
        f"app=vantage6-store,release={ctx.helm_release_name},component=store",
        k8s_config,
    )
    _wait_for_component_ready(
        "HQ",
        f"app=vantage6-hq,release={ctx.helm_release_name},component=vantage6-hq",
        k8s_config,
    )
    info("Hub services are ready.")


# TODO refactor this, I think something similar is in other file
def _kubectl(
    args: list[str], k8s_config, check: bool = True
) -> subprocess.CompletedProcess:
    """
    Run a kubectl command with optional context/namespace from k8s_config.
    """

    cmd = ["kubectl"] + args
    if k8s_config.context:
        cmd.extend(["--context", k8s_config.context])
    if k8s_config.namespace:
        cmd.extend(["--namespace", k8s_config.namespace])
    return subprocess.run(
        cmd,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _wait_for_pod_ready(selector: str, description: str, k8s_config) -> None:
    """
    Wait for at least one pod matching the selector to be created and become Ready.
    """

    info(f"Waiting for {description} pod(s) to be created...")
    while True:
        result = _kubectl(
            ["get", "pod", "-l", selector, "-o", "name"],
            k8s_config,
            check=False,
        )
        if result.stdout.strip():
            break
        time.sleep(2)

    info(f"{description} pod(s) created, waiting for them to become Ready...")
    try:
        _kubectl(
            [
                "wait",
                "--for=condition=ready",
                "pod",
                "-l",
                selector,
                "--timeout",
                "600s",
            ],
            k8s_config,
            check=True,
        )
    except subprocess.CalledProcessError:
        warning(f"Timeout while waiting for {description} pod(s) to become Ready.")


def _wait_for_keycloak_ready(release_name: str, k8s_config) -> None:
    """
    Ensure Keycloak pod is ready and realm import job finished.
    """

    selector = f"app.kubernetes.io/instance={release_name}-kc"
    job_name = f"{release_name}-realm-import"

    _wait_for_pod_ready(selector, "Keycloak", k8s_config)

    info("Waiting for Keycloak realm import job to be created...")
    while True:
        result = _kubectl(["get", "job", job_name], k8s_config, check=False)
        if result.returncode == 0:
            break
        time.sleep(2)

    info("Keycloak realm import job was created, waiting for it to finish...")
    job_check = _kubectl(["get", "job", job_name], k8s_config, check=False)
    if job_check.returncode == 0:
        try:
            _kubectl(
                [
                    "wait",
                    "--for=condition=complete",
                    f"job/{job_name}",
                    "--timeout",
                    "300s",
                ],
                k8s_config,
                check=True,
            )
            info("Realm import job completed successfully.")
        except subprocess.CalledProcessError:
            warning(
                "Realm import job did not complete in time; continuing hub startup."
            )
    else:
        info("No realm import job found (realm import may be disabled).")


def _wait_for_component_ready(name: str, selector: str, k8s_config) -> None:
    """
    Wait for a hub component (HQ or Store) to be ready.
    """

    _wait_for_pod_ready(selector, name, k8s_config)
