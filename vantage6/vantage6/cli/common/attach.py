from subprocess import Popen

from vantage6.common import Fore, Style, error
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import (
    extract_name_and_is_sandbox,
    find_running_service_names,
    select_running_service,
)
from vantage6.cli.context import get_context
from vantage6.cli.globals import InfraComponentName
from vantage6.cli.k8s_config import KubernetesConfig


def attach_logs(
    name: str | None,
    instance_type: InstanceType,
    infra_component: InfraComponentName,
    k8s_config: KubernetesConfig,
    system_folders: bool,
    is_sandbox: bool = False,
    additional_labels: str | None = None,
) -> None:
    """
    Attach to the logs of the given labels.

    Parameters
    ----------
    name : str | None
        The name of the service to attach to. If None, the user will be asked to
        select a service.
    instance_type : InstanceType
        The instance type of the service.
    infra_component : InfraComponentName
        The infra component of the service.
    system_folders : bool
        Whether to use system folders.
    k8s_config : KubernetesConfig
        The Kubernetes configuration.
    is_sandbox : bool
        Whether the configuration is a sandbox configuration, by default False
    additional_labels : str | None
        Additional labels to filter the logs by.
    """
    running_services = find_running_service_names(
        instance_type=instance_type,
        only_system_folders=system_folders,
        only_user_folders=not system_folders,
        k8s_config=k8s_config,
    )

    if not running_services:
        error(f"No running {infra_component.value}s found.")
        return

    if not name:
        helm_name = select_running_service(running_services, instance_type)
    else:
        name, is_sandbox = extract_name_and_is_sandbox(name, is_sandbox)
        ctx = get_context(instance_type, name, system_folders, is_sandbox=is_sandbox)
        helm_name = ctx.helm_release_name

    if helm_name in running_services:
        _attach_logs(helm_name, k8s_config, additional_labels)
    else:
        error(f"{Fore.RED}{helm_name}{Style.RESET_ALL} is not running?!")


def _attach_logs(
    service: str, k8s_config: KubernetesConfig, additional_labels: str | None = None
) -> None:
    """
    Attach to the logs of the given service.

    Parameters
    ----------
    service : str
        The name of the service to attach to.
    k8s_config : KubernetesConfig
        The Kubernetes configuration.
    additional_labels : str | None
        Additional labels to filter the logs by.
    """
    labels = f"release={service}"
    if additional_labels:
        labels += f",{additional_labels}"
    # Stream logs from all pods that belong to this Helm release, within the
    # provided namespace and context. Using label selection ensures we attach
    # to pods rather than higher-level resources.
    command = [
        "kubectl",
        "--context",
        k8s_config.last_context,
        "-n",
        k8s_config.last_namespace,
        "logs",
        "--follow",
        "--selector",
        labels,
        "--all-containers=true",
    ]
    process = Popen(command, stdout=None, stderr=None)
    process.wait()
