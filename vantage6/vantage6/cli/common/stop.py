from __future__ import annotations

import subprocess

from colorama import Fore, Style

from vantage6.common import error, info, warning
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import (
    find_running_service_names,
    select_context_and_namespace,
    select_running_service,
)
from vantage6.cli.context import get_context
from vantage6.cli.globals import InfraComponentName
from vantage6.cli.utils import validate_input_cmd_args


def execute_stop(
    stop_function: callable,
    instance_type: InstanceType,
    infra_component: InfraComponentName,
    stop_all: bool,
    to_stop: str | None,
    namespace: str,
    context: str,
    system_folders: bool,
):
    """
    Execute the stop function for a given instance type and infra component.

    Parameters
    ----------
    stop_function : callable
        The function to stop the service.
    instance_type : InstanceType
        The instance type of the service.
    infra_component : InfraComponentName
        The infra component of the service.
    stop_all : bool
        Whether to stop all services.
    to_stop : str | None
        The name of the service to stop.
    namespace : str
        The namespace of the service.
    context : str
        The context of the service.
    system_folders : bool
        Whether to use system folders.
    """
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    running_services = find_running_service_names(
        instance_type=instance_type,
        only_system_folders=system_folders,
        only_user_folders=not system_folders,
        context=context,
        namespace=namespace,
    )

    if not running_services:
        error(f"No running {infra_component.value}s found.")
        return

    if stop_all:
        for service in running_services:
            stop_function(service, namespace, context)
    else:
        if not to_stop:
            helm_name = select_running_service(running_services, instance_type)
        else:
            ctx = get_context(instance_type, to_stop, system_folders)
            helm_name = ctx.helm_release_name

        if helm_name in running_services:
            stop_function(helm_name, namespace, context)
            info(
                f"Stopped the {Fore.GREEN}{helm_name}{Style.RESET_ALL} {infra_component.value}."
            )
        else:
            error(f"{Fore.RED}{to_stop}{Style.RESET_ALL} is not running?!")


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
