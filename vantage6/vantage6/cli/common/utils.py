import questionary as q
from colorama import Fore, Style
import click
from typing import Iterable
import docker


from vantage6.common import warning, error
from vantage6.common.globals import APPNAME, InstanceType, STRING_ENCODING
from vantage6.cli.context import select_context_class


def get_server_name(
    name: str,
    system_folders: bool,
    running_server_names: list[str],
    instance_type: InstanceType,
) -> str:
    """
    Get the version of a running server.

    Parameters
    ----------
    name : str
        Name of the server to get the version from
    system_folders : bool
        Whether to use system folders or not
    running_server_names : list[str]
        The names of the running servers
    instance_type : InstanceType
        The type of instance to get the running servers from
    """

    if not name:
        if not running_server_names:
            error(
                f"No {instance_type}s are running! You can only check the version for "
                f"{instance_type}s that are running"
            )
            exit(1)
        try:
            name = q.select(
                f"Select the {instance_type} you wish to inspect:",
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
        filters={"label": f"{APPNAME}-type={instance_type}"}
    )
    return [server.name for server in running_servers]


def get_server_configuration_list(instance_type: InstanceType.SERVER) -> None:
    """
    Print list of available server configurations.

    Parameters
    ----------
    instance_type : InstanceType
        The type of instance to get the configurations for
    """
    client = docker.from_env()
    ctx_class = select_context_class(instance_type)

    running_server_names = get_running_servers(client, instance_type)
    header = "\nName" + (21 * " ") + "Status" + (10 * " ") + "System/User"

    click.echo(header)
    click.echo("-" * len(header))

    running = Fore.GREEN + "Running" + Style.RESET_ALL
    stopped = Fore.RED + "Not running" + Style.RESET_ALL

    # system folders
    configs, f1 = ctx_class.available_configurations(system_folders=True)
    for config in configs:
        status = (
            running
            if f"{APPNAME}-{config.name}-system-{instance_type}" in running_server_names
            else stopped
        )
        click.echo(f"{config.name:25}" f"{status:25} System ")

    # user folders
    configs, f2 = ctx_class.available_configurations(system_folders=False)
    for config in configs:
        status = (
            running
            if f"{APPNAME}-{config.name}-user-{instance_type}" in running_server_names
            else stopped
        )
        click.echo(f"{config.name:25}" f"{status:25} User   ")

    click.echo("-" * 85)
    if len(f1) + len(f2):
        warning(f"{Fore.RED}Failed imports: {len(f1)+len(f2)}{Style.RESET_ALL}")


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
