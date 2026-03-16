import subprocess
import time

from vantage6.common import error, info, warning

from vantage6.cli.k8s_config import KubernetesConfig


def run_kubectl_command(
    args: list[str],
    k8s_config: KubernetesConfig,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run a kubectl command with the appropriate context and namespace.

    Parameters
    ----------
    command : list[str]
        The kubectl command to run (without 'kubectl' prefix if already included).
    k8s_config: KubernetesConfig
        Kubernetes configuration object with context and namespace.
    check : bool
        Whether to raise an exception on non-zero exit code.

    Returns
    -------
    subprocess.CompletedProcess
        The result of the subprocess call.

    Raises
    ------
    subprocess.CalledProcessError
        If the command fails and check is True.
    """
    command = ["kubectl"] + args
    if k8s_config.context:
        command.extend(["--context", k8s_config.context])

    if k8s_config.namespace:
        command.extend(["--namespace", k8s_config.namespace])

    try:
        result = subprocess.run(
            command,
            check=check,
            capture_output=True,
            text=True,
        )
        return result
    except subprocess.CalledProcessError as e:
        error(f"Command failed: {' '.join(command)}")
        if e.stderr:
            error(f"Error: {e.stderr}")
        if check:
            raise
        return e


def wait_for_pod_ready(
    selector: str, description: str, k8s_config: KubernetesConfig
) -> None:
    """
    Wait for at least one pod matching the selector to be created and become Ready.

    Parameters
    ----------
    selector : str
        The selector to use to find the pods.
    description : str
        The description of the pods to wait for.
    k8s_config : KubernetesConfig
        The Kubernetes configuration to use.
    """

    info(f"Waiting for {description} pod(s) to be created...")
    attempt = 0
    max_attempts = 20
    while attempt < max_attempts:
        result = run_kubectl_command(
            ["get", "pod", "-l", selector, "-o", "name"],
            k8s_config,
            check=False,
        )
        if result.stdout.strip():
            break
        time.sleep(2)
        attempt += 1
        if attempt == max_attempts:
            error(f"Timeout while waiting for {description} pod(s) to be created.")
            exit(1)

    info(f"{description} pod(s) created, waiting for them to become Ready...")
    try:
        run_kubectl_command(
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
