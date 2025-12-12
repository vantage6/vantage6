from __future__ import annotations

import subprocess
from collections.abc import Callable

from colorama import Fore, Style

from vantage6.common import error, info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import (
    extract_name_and_is_sandbox,
    find_running_service_names,
    select_running_service,
)
from vantage6.cli.context import get_context
from vantage6.cli.globals import CLICommandName, InfraComponentName
from vantage6.cli.k8s_config import KubernetesConfig, select_k8s_config
from vantage6.cli.utils import validate_input_cmd_args


def execute_cli_stop(
    command_name: CLICommandName,
    name: str,
    k8s_config: KubernetesConfig,
    system_folders: bool,
    is_sandbox: bool = False,
) -> None:
    """
    Execute the stop command for an infrastructure service.
    """
    cmd = [
        "v6",
        command_name.value,
        "stop",
        "--name",
        name,
        "--context",
        k8s_config.context,
        "--namespace",
        k8s_config.namespace,
    ]
    cmd.append("--system" if system_folders else "--user")
    if is_sandbox:
        cmd.append("--sandbox")
    subprocess.run(cmd, check=True)


def execute_stop(
    stop_function: Callable,
    instance_type: InstanceType,
    infra_component: InfraComponentName,
    stop_all: bool,
    to_stop: str | None,
    namespace: str,
    context: str,
    system_folders: bool,
    is_sandbox: bool = False,
    stop_function_args: dict | None = None,
):
    """
    Execute the stop function for a given instance type and infra component.

    Parameters
    ----------
    stop_function : Callable
        The function to stop the service.
    instance_type : InstanceType
        The instance type of the service.
    infra_component : InfraComponentName
        The infra component of the service.
    stop_all : bool
        Whether to stop all services.
    to_stop : str | None
        The name of the service to stop. If None, the user will be asked to select a
        service.
    namespace : str
        The namespace of the service.
    context : str
        The context of the service.
    system_folders : bool
        Whether to use system folders.
    is_sandbox : bool
        Whether the configuration is a sandbox configuration, by default False
    stop_function_args : dict | None
        Additional arguments to pass to the stop function
    """
    if stop_function_args is None:
        stop_function_args = {}
    k8s_config = select_k8s_config(
        context=context,
        namespace=namespace,
    )
    running_services = find_running_service_names(
        instance_type=instance_type,
        only_system_folders=system_folders,
        only_user_folders=not system_folders,
        k8s_config=k8s_config,
    )

    if not running_services:
        error(f"No running {infra_component.value}s found.")
        return

    if stop_all:
        for service in running_services:
            stop_function(service, k8s_config.namespace, k8s_config.context)
    else:
        if not to_stop:
            helm_name = select_running_service(running_services, instance_type)
        else:
            to_stop, is_sandbox = extract_name_and_is_sandbox(to_stop, is_sandbox)
            ctx = get_context(
                instance_type, to_stop, system_folders, is_sandbox=is_sandbox
            )
            helm_name = ctx.helm_release_name

        if helm_name in running_services:
            stop_function(
                helm_name,
                k8s_config,
                **stop_function_args,
            )
            info(
                f"Stopped the {Fore.GREEN}{helm_name}{Style.RESET_ALL} "
                f"{infra_component.value}."
            )
        else:
            error(f"{Fore.RED}{to_stop}{Style.RESET_ALL} is not running?!")


def helm_uninstall(
    release_name: str, k8s_config: KubernetesConfig | None = None
) -> None:
    """
    Manage the `helm uninstall` command.

    Parameters
    ----------
    release_name : str
        The name of the Helm release to uninstall.
    k8s_config : KubernetesConfig, optional
        The Kubernetes configuration to use.
    """
    # Input validation
    validate_input_cmd_args(release_name, "release name")
    if k8s_config:
        validate_input_cmd_args(k8s_config.context, "context name", allow_none=True)
        validate_input_cmd_args(k8s_config.namespace, "namespace name", allow_none=True)

    # Create the command
    max_time_stop = "60s"
    info(
        f"Stopping helm chart '{release_name}'. This may take up to {max_time_stop}..."
    )
    command = ["helm", "uninstall", release_name, "--wait", "--timeout", max_time_stop]

    if k8s_config and k8s_config.context:
        command.extend(["--kube-context", k8s_config.context])

    if k8s_config and k8s_config.namespace:
        command.extend(["--namespace", k8s_config.namespace])

    try:
        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        info(f"Successfully uninstalled release '{release_name}'.")
    except subprocess.CalledProcessError as e:
        error(f"Failed to uninstall release '{release_name}': {e}")
    except FileNotFoundError:
        error(
            "Helm command not found. Please ensure Helm is installed and available in "
            "the PATH."
        )
