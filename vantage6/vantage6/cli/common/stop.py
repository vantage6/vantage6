from __future__ import annotations

import subprocess

from vantage6.common import error, info, warning

from vantage6.cli.utils import validate_input_cmd_args


def stop_port_forward(service_name: str) -> None:
    """
    Stop the port forwarding process for a given service name.

    Parameters
    ----------
    service_name : str
        The name of the service whose port forwarding process should be terminated.
    """
    # Input validation
    validate_input_cmd_args(service_name, "service name")

    try:
        # Find the process ID (PID) of the port forwarding command
        result = subprocess.run(
            ["pgrep", "-f", f"kubectl port-forward.*{service_name}"],
            check=True,
            text=True,
            capture_output=True,
        )
        pids = result.stdout.strip().splitlines()

        if not pids:
            warning(f"No port forwarding process found for service '{service_name}'.")
            return

        for pid in pids:
            subprocess.run(["kill", "-9", pid], check=True)
            info(
                f"Terminated port forwarding process for service '{service_name}' "
                f"(PID: {pid})"
            )
    except subprocess.CalledProcessError as e:
        error(f"Failed to terminate port forwarding: {e}")


def helm_uninstall(
    release_name: str,
    context: str | None = None,
    namespace: str | None = None,
) -> None:
    """
    Manage the `helm uninstall` command.

    Parameters
    ----------
    release_name : str
        The name of the Helm release to uninstall.
    context : str, optional
        The Kubernetes context to use.
    namespace : str, optional
        The Kubernetes namespace to use.
    """
    # Input validation
    validate_input_cmd_args(release_name, "release name")
    validate_input_cmd_args(context, "context name", allow_none=True)
    validate_input_cmd_args(namespace, "namespace name", allow_none=True)

    # Create the command
    command = ["helm", "uninstall", release_name]

    if context:
        command.extend(["--kube-context", context])

    if namespace:
        command.extend(["--namespace", namespace])

    try:
        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        info(f"Successfully uninstalled release '{release_name}'.")
    except subprocess.CalledProcessError as e:
        error(f"Failed to uninstall release '{release_name}': {e.stderr}")
    except FileNotFoundError:
        error(
            "Helm command not found. Please ensure Helm is installed and available in "
            "the PATH."
        )
