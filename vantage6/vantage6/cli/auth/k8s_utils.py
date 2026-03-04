import subprocess
import time

from vantage6.common import info, warning

from vantage6.cli.common.k8s_utils import run_kubectl_command
from vantage6.cli.k8s_config import KubernetesConfig


def wait_for_keycloak_ready(release_name: str, k8s_config: KubernetesConfig) -> None:
    """
    Ensure Keycloak pod is ready and realm import job finished.

    Parameters
    ----------
    release_name : str
        The name of the release.
    k8s_config : KubernetesConfig
        The Kubernetes configuration to use.
    """
    selector = f"app.kubernetes.io/instance={release_name}-kc"
    job_name = f"{release_name}-realm-import"

    info("Waiting for Keycloak pod to be created...")
    while True:
        result = run_kubectl_command(["get", "pod", "-l", selector], k8s_config)
        if result.returncode == 0:
            break
        else:
            time.sleep(1)
    info("Keycloak pod was created, waiting for it to be ready...")
    run_kubectl_command(
        ["wait", "--for=condition=ready", "pod", "-l", selector, "--timeout", "300s"],
        k8s_config,
    )

    info("Waiting for Keycloak realm import job to be created...")
    while True:
        result = run_kubectl_command(["get", "job", job_name], k8s_config, check=False)
        if result.returncode == 0:
            break
        else:
            time.sleep(1)
    info("Keycloak realm import job was created, waiting for it to finish...")
    # Check if the job exists first (don't raise exception if it doesn't)
    job_check = run_kubectl_command(["get", "job", job_name], k8s_config, check=False)
    if job_check.returncode == 0:
        # Job exists, wait for it to complete
        try:
            run_kubectl_command(
                [
                    "wait",
                    "--for=condition=complete",
                    f"job/{job_name}",
                    "--timeout",
                    "120s",
                ],
                k8s_config,
            )
            info("Realm import job completed successfully.")
        except subprocess.CalledProcessError:
            warning("Realm import job did not complete in time; continuing startup.")
    else:
        info("No realm import job found (realm import may be disabled).")
