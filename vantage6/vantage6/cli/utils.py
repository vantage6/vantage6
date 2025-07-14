"""
Utility functions for the CLI
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from os import PathLike
from pathlib import Path

import questionary as q

import docker
from vantage6.common import error, info, warning
from vantage6.common.globals import DEFAULT_CHART_REPO


def check_config_name_allowed(name: str) -> None:
    """
    Check if configuration name is allowed

    Parameters
    ----------
    name : str
        Name to be checked
    """
    if name.count(" ") > 0:
        name = name.replace(" ", "-")
        info(f"Replaced spaces from configuration name: {name}")
    if not re.match("^[a-zA-Z0-9_.-]+$", name):
        error(
            f"Name '{name}' is not allowed. Please use only the following "
            "characters: a-zA-Z0-9_.-"
        )
        # FIXME: FM, 2023-01-03: I dont think this is a good side effect. This
        # should be handled by the caller.
        exit(1)


def check_if_docker_daemon_is_running(docker_client: docker.DockerClient) -> None:
    """
    Check if Docker daemon is running

    Parameters
    ----------
    docker_client : docker.DockerClient
        The docker client
    """
    try:
        docker_client.ping()
    except Exception:
        error("Docker socket can not be found. Make sure Docker is running.")
        exit(1)


def remove_file(file: str | Path, file_type: str) -> None:
    """
    Remove a file if it exists.

    Parameters
    ----------
    file : str
        absolute path to the file to be deleted
    file_type : str
        type of file, used for logging
    """
    if os.path.isfile(file):
        info(f"Removing {file_type} file: {file}")
        try:
            os.remove(file)
        except Exception as e:
            error(f"Could not delete file: {file}")
            error(e)
    else:
        warning(f"Could not remove {file_type} file: {file} does not exist")


def prompt_config_name(name: str | None) -> None:
    """
    Get a new configuration name from the user, or simply return the name if
    it is not None.

    Parameters
    ----------
    name : str
        Name to be checked

    Returns
    -------
    str
        The name of the configuration
    """
    if not name:
        try:
            name = q.text("Please enter a configuration-name:").unsafe_ask()
        except KeyboardInterrupt:
            error("Aborted by user!")
            exit(1)
        if name.count(" ") > 0:
            name = name.replace(" ", "-")
            info(f"Replaced spaces from configuration name: {name}")
    return name


def switch_context_and_namespace(
    context: str | None = None, namespace: str | None = None
) -> None:
    # input validation
    _validate_input(context, "context name", allow_none=True)
    _validate_input(namespace, "namespace name", allow_none=True)

    try:
        if context:
            subprocess.run(
                ["kubectl", "config", "use-context", context],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            info(f"Successfully set context to: {context}")

        if namespace:
            subprocess.run(
                [
                    "kubectl",
                    "config",
                    "set-context",
                    context or "--current",
                    f"--namespace={namespace}",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            info(f"Successfully set namespace to: {namespace}")

    except subprocess.CalledProcessError as e:
        error(f"Failed to set Kubernetes context or namespace: {e}")


def start_port_forward(
    service_name: str,
    service_port: int,
    port: int,
    ip: str | None,
    context: str | None = None,
    namespace: str | None = None,
) -> subprocess.Popen | None:
    """
    Port forward a kubernetes service.

    Parameters
    ----------
    service_name : str
        The name of the Kubernetes service to port forward.
    service_port : int
        The port on the service to forward.
    port : int
        The port to listen on.
    ip : str | None
        The IP address to listen on. If None, defaults to localhost.
    context : str | None
        The Kubernetes context to use.
    namespace : str | None
        The Kubernetes namespace to use.

    Returns
    -------
    subprocess.Popen | None
        The background process object if successful, None if failed.
    """
    # Input validation
    _validate_input(service_name, "service name")
    if not isinstance(service_port, int) or service_port <= 0:
        error(f"Invalid service port: {service_port}. Must be a positive integer.")
        return

    if not isinstance(port, int) or port <= 0:
        error(f"Invalid local port: {port}. Must be a positive integer.")
        return

    if ip and not re.match(
        r"^(localhost|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})$", ip
    ):
        error(f"Invalid IP address: {ip}. Must be a valid IPv4 address or 'localhost'.")
        return

    _validate_input(context, "context name", allow_none=True)
    _validate_input(namespace, "namespace name", allow_none=True)

    # Check if the service is ready before starting port forwarding
    info(f"Waiting for service '{service_name}' to become ready...")
    start_time = time.time()
    timeout = 300  # seconds
    while time.time() - start_time < timeout:
        try:
            result = (
                subprocess.check_output(
                    [
                        "kubectl",
                        "get",
                        "endpoints",
                        service_name,
                        "-o",
                        "jsonpath={.subsets[*].addresses[*].ip}",
                    ]
                )
                .decode()
                .strip()
            )

            if result:
                info(f"Service '{service_name}' is ready.")
                break
        except subprocess.CalledProcessError:
            pass  # ignore and retry

        time.sleep(2)
    else:
        error(
            f"Timeout: Service '{service_name}' has no ready endpoints after {timeout} seconds."
        )
        return

    # Create the port forwarding command
    if not ip:
        ip = "localhost"

    command = [
        "kubectl",
        "port-forward",
        "--address",
        ip,
        f"service/{service_name}",
        f"{port}:{service_port}",
    ]

    if context:
        command.extend(["--context", context])

    if namespace:
        command.extend(["--namespace", namespace])

    # Start the port forwarding process
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            start_new_session=True,  # Start in new session to detach from parent
        )

        # Give the process a moment to start and check if it's still running
        time.sleep(1)
        if process.poll() is not None:
            # Process has already terminated
            e = process.stderr.read().decode() if process.stderr else "Unknown error"
            error(f"Failed to start port forwarding: {e}")
            return

        info(
            f"Port forwarding started: {ip}:{port} -> {service_name}:{service_port} "
            f"(PID: {str(process.pid)})"
        )
        return
    except Exception as e:
        error(f"Failed to start port forwarding: {e}")
        return


def stop_port_forward(service_name: str) -> None:
    """
    Stop the port forwarding process for a given service name.

    Parameters
    ----------
    service_name : str
        The name of the service whose port forwarding process should be terminated.
    """
    # Input validation
    _validate_input(service_name, "service name")

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


def helm_install(
    release_name: str,
    chart_name: str,
    values_file: str | PathLike | None = None,
    context: str | None = None,
    namespace: str | None = None,
) -> None:
    """
    Manage the `helm install` command.

    Parameters
    ----------
    release_name : str
        The name of the Helm release.
    chart_name : str
        The name of the Helm chart.
    values_file : str, optional
        A single values file to use with the `-f` flag.
    context : str, optional
        The Kubernetes context to use.
    namespace : str, optional
        The Kubernetes namespace to use.
    """
    # Input validation
    _validate_input(release_name, "release name")
    _validate_input(chart_name, "chart name")

    values_file = Path(values_file) if values_file else None
    if values_file and not values_file.is_file():
        error(f"Helm chart values file does not exist: {values_file}")
        return

    _validate_input(context, "context name", allow_none=True)
    _validate_input(namespace, "namespace name", allow_none=True)

    # Create the command
    command = [
        "helm",
        "install",
        release_name,
        chart_name,
        "--repo",
        DEFAULT_CHART_REPO,
        "--devel",  # ensure using latest version including pre-releases
    ]

    if values_file:
        command.extend(["-f", str(values_file)])

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
        info(
            f"Successfully installed release '{release_name}' using chart '{chart_name}'."
        )
    except subprocess.CalledProcessError as e:
        error(f"Failed to install release '{release_name}': {e.stderr}")
    except FileNotFoundError:
        error(
            "Helm command not found. Please ensure Helm is installed and available in the PATH."
        )


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
    _validate_input(release_name, "release name")
    _validate_input(context, "context name", allow_none=True)
    _validate_input(namespace, "namespace name", allow_none=True)

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
            "Helm command not found. Please ensure Helm is installed and available in the PATH."
        )


def _validate_input(
    value: str | None, field_name: str, allow_none: bool = False
) -> None:
    """
    Validate input for subprocess commands.

    Parameters
    ----------
    value : str | None
        The value to validate.
    field_name : str
        The name of the field being validated, used for error messages.
    allow_none : bool, optional
        Whether None is allowed as a valid value. Defaults to False.

    Raises
    ------
    SystemExit
        If the input is invalid.
    """
    if allow_none and value is None:
        return

    if not isinstance(value, str) or not re.match("^[a-zA-Z0-9_.-]+$", value):
        error(
            f"Invalid {field_name}: {value}. Use only alphanumeric characters, "
            "dashes, underscores, or dots."
        )
        exit(1)
