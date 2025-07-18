"""
Utility functions for the CLI
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import docker
import questionary as q

from vantage6.common import error, info, warning


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
