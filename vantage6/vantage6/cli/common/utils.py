import json
import subprocess
from pathlib import Path
from subprocess import Popen
from typing import Iterable

import click
import docker
import questionary as q
from colorama import Fore, Style

from vantage6.common import error, warning
from vantage6.common.globals import APPNAME, STRING_ENCODING, InstanceType

from vantage6.cli.config import CliConfig
from vantage6.cli.context import select_context_class
from vantage6.cli.utils import validate_input_cmd_args


def select_context_and_namespace(
    context: str | None = None,
    namespace: str | None = None,
) -> tuple[str, str]:
    """
    Select the context and namespace to use.

    This uses the CLI config to compare the provided context and namespace with the
    last used context and namespace. If the provided context and namespace are not
    the same as the last used context and namespace, the CLI config is updated.

    Parameters
    ----------
    context : str, optional
        The Kubernetes context to use.
    namespace : str, optional
        The Kubernetes namespace to use.

    Returns
    -------
    tuple[str, str]
        The context and namespace to use
    """
    cli_config = CliConfig()

    return cli_config.compare_changes_config(
        context=context,
        namespace=namespace,
    )


def create_directory_if_not_exists(directory: Path) -> None:
    """
    Create a directory.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        error(f"Failed to create directory {directory}: {e}")
        exit(1)


def find_running_service_names(
    instance_type: InstanceType,
    only_system_folders: bool = False,
    only_user_folders: bool = False,
    context: str | None = None,
    namespace: str | None = None,
) -> list[str]:
    """
    List running Vantage6 servers.

    Parameters
    ----------
    instance_type : InstanceType
        The type of instance to find running services for
    only_system_folders : bool, optional
        Whether to look for system-based services or not. By default False.
    only_user_folders : bool, optional
        Whether to look for user-based services or not. By default False.
    context : str, optional
        The Kubernetes context to use.
    namespace : str, optional
        The Kubernetes namespace to use.

    Returns
    -------
    list[str]
        List of release names that are running
    """
    # Input validation
    validate_input_cmd_args(context, "context name", allow_none=True)
    validate_input_cmd_args(namespace, "namespace name", allow_none=True)
    validate_input_cmd_args(instance_type, "instance type", allow_none=False)
    if only_system_folders and only_user_folders:
        error("Cannot use both only_system_folders and only_user_folders")
        exit(1)

    # Create the command
    command = [
        "helm",
        "list",
        "--output",
        "json",  # Get structured output
    ]

    if context:
        command.extend(["--kube-context", context])

    if namespace:
        command.extend(["--namespace", namespace])
    else:
        command.extend(["--all-namespaces"])

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        error(f"Failed to list Helm releases: {e}")
        return []
    except FileNotFoundError:
        error(
            "Helm command not found. Please ensure Helm is installed and available in "
            "the PATH."
        )
        return []

    try:
        releases = json.loads(result.stdout)
    except json.JSONDecodeError:
        error("Failed to parse Helm output as JSON")
        return []

    # filter services for the vantage6 services that are sought. These have
    # the following pattern:
    # f"{APPNAME}-{name}-{scope}-{instance_type.value}"

    # filter for the instance type
    svc_starts_with = f"{APPNAME}-"
    if only_system_folders:
        svc_ends_with = f"system-{instance_type.value}"
    elif only_user_folders:
        svc_ends_with = f"user-{instance_type.value}"
    else:
        svc_ends_with = f"-{instance_type.value}"

    matching_services = []
    for release in releases:
        release_name = release.get("name", "")

        # Check if this is a Vantage6 server release
        is_matching_service = (
            release_name.startswith(svc_starts_with)
            and release_name.endswith(svc_ends_with)
            and instance_type.value in release_name
        )

        if is_matching_service:
            matching_services.append(release_name)

    return matching_services


def select_running_service(
    running_services: list[str],
    instance_type: InstanceType,
) -> str:
    """
    Select a running service from the list of running services.
    """
    try:
        name = q.select(
            f"Select the {instance_type.value} you wish to inspect:",
            choices=running_services,
        ).unsafe_ask()
    except KeyboardInterrupt:
        error("Aborted by user!")
        exit(1)
    return name


def get_server_name(
    name: str,
    system_folders: bool,
    running_server_names: list[str],
    instance_type: InstanceType,
) -> str:
    """
    Get the full name of a running server.

    Parameters
    ----------
    name : str
        Name of the server to get the full name from
    system_folders : bool
        Whether to use system folders or not
    running_server_names : list[str]
        The names of the running servers
    instance_type : InstanceType
        The type of instance to get the full name from
    """

    if not name:
        if not running_server_names:
            error(
                f"No {instance_type.value}s are running! You can only check the version"
                f" for {instance_type.value}s that are running"
            )
            exit(1)
        try:
            name = q.select(
                f"Select the {instance_type.value} you wish to inspect:",
                choices=running_server_names,
            ).unsafe_ask()
        except KeyboardInterrupt:
            error("Aborted by user!")
            exit(1)
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}"
    return name


def get_running_servers(
    client: docker.DockerClient, instance_type: InstanceType
) -> list[str]:
    """Get the running servers of a certain type.

    Parameters
    ----------
    client : docker.DockerClient
        The docker client to use
    instance_type : InstanceType
        The type of instance to get the running servers from

    Returns
    -------
    list[str]
        The names of the running servers
    """
    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type={instance_type.value}"}
    )
    return [server.name for server in running_servers]


def get_server_configuration_list(instance_type: InstanceType) -> None:
    """
    Print list of available server configurations.

    Parameters
    ----------
    instance_type : InstanceType
        The type of instance to get the configurations for
    """
    ctx_class = select_context_class(instance_type)

    running_server_names = find_running_service_names(instance_type)
    header = "\nName" + (21 * " ") + "Status" + (10 * " ") + "System/User"

    click.echo(header)
    click.echo("-" * len(header))

    running = Fore.GREEN + "Running" + Style.RESET_ALL
    stopped = Fore.RED + "Not running" + Style.RESET_ALL

    # system folders
    configs, failed_imports_system = ctx_class.available_configurations(
        system_folders=True
    )
    for config in configs:
        status = (
            running
            if f"{APPNAME}-{config.name}-system-{instance_type.value}"
            in running_server_names
            else stopped
        )
        click.echo(f"{config.name:25}{status:25} System ")

    # user folders
    configs, failed_imports_user = ctx_class.available_configurations(
        system_folders=False
    )
    for config in configs:
        status = (
            running
            if f"{APPNAME}-{config.name}-user-{instance_type.value}"
            in running_server_names
            else stopped
        )
        click.echo(f"{config.name:25}{status:25} User   ")

    click.echo("-" * 85)
    if len(failed_imports_system) + len(failed_imports_user):
        warning(
            f"{Fore.RED}Failed imports: "
            f"{len(failed_imports_system) + len(failed_imports_user)}{Style.RESET_ALL}"
        )


def print_log_worker(logs_stream: Iterable[bytes]) -> None:
    """
    Print the logs from the logs stream.

    Parameters
    ----------
    logs_stream : Iterable[bytes]
        Output of the container.attach() method
    """
    for log in logs_stream:
        try:
            print(log.decode(STRING_ENCODING), end="")
        except UnicodeDecodeError:
            print(
                "ERROR DECODING LOGS!!! Printing raw bytes. Please check the logs in "
                "the container."
            )
            print(log)


def get_name_from_container_name(container_name: str) -> str:
    """
    Get the node/server/store name from a container name.

    Parameters
    ----------
    container_name : str
        The name of the container

    Returns
    -------
    str
        The name of the node/server/store
    """
    # Container name is structured as: f"{APPNAME}-{name}-{post_fix}"
    # Take into account that name can contain '-'
    return "-".join(container_name.split("-")[1:-1])


def attach_logs(*labels: list[str]) -> None:
    """
    Attach to the logs of the given labels.

    Parameters
    ----------
    labels : list[str]
        The labels to attach to
    """
    command = ["kubectl", "logs", "--follow", "--selector", ",".join(labels)]
    process = Popen(command, stdout=None, stderr=None)
    process.wait()


def get_main_cli_command_name(instance_type: InstanceType) -> str:
    """
    Get the main CLI command name for a given instance type.

    Parameters
    ----------
    instance_type : InstanceType
        The type of instance to get the main CLI command name for
    """
    if instance_type == InstanceType.SERVER:
        return "server"
    elif instance_type == InstanceType.ALGORITHM_STORE:
        return "algorithm-store"
    elif instance_type == InstanceType.NODE:
        return "node"
    else:
        raise ValueError(f"Invalid instance type: {instance_type}")
