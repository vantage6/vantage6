import click
from colorama import Fore, Style

from vantage6.common import warning
from vantage6.common.globals import (
    APPNAME,
    SANDBOX_SUFFIX,
    InstanceType,
)

from vantage6.cli.common.utils import find_running_service_names
from vantage6.cli.context import select_context_class


def get_configuration_list(instance_type: InstanceType) -> None:
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
        config.name = config.name.replace(SANDBOX_SUFFIX, "")
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
        config.name = config.name.replace(SANDBOX_SUFFIX, "")
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
