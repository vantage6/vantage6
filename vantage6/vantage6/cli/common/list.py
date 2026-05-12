import click
from colorama import Fore, Style

from vantage6.common import warning
from vantage6.common.context import AppContext
from vantage6.common.globals import (
    APPNAME,
    SANDBOX_SUFFIX,
    InstanceType,
)
from vantage6.common.kubernetes.utils import running_in_wsl

from vantage6.cli.common.utils import find_running_service_names
from vantage6.cli.context import select_context_class


def get_configuration_list(instance_type: InstanceType) -> None:
    """
    Print list of available configurations.

    Parameters
    ----------
    instance_type : InstanceType
        The type of instance to get the configurations for
    """
    ctx_class = select_context_class(instance_type)

    running_service_names = find_running_service_names(instance_type)
    header = "\nName" + (21 * " ") + "Status" + (10 * " ") + "System/User"

    click.echo(header)
    click.echo("-" * len(header))

    # system folders
    if running_in_wsl():
        # for WSL, there is no distinction between user and system folders, so we
        # only print the user folders
        failed_imports = _print_configs(
            ctx_class=ctx_class,
            system_folders=False,
            running_service_names=running_service_names,
            instance_type=instance_type,
        )
    else:
        failed_imports_system = _print_configs(
            ctx_class=ctx_class,
            system_folders=True,
            running_service_names=running_service_names,
            instance_type=instance_type,
        )
        failed_imports_user = _print_configs(
            ctx_class=ctx_class,
            system_folders=False,
            running_service_names=running_service_names,
            instance_type=instance_type,
        )
        failed_imports = failed_imports_system + failed_imports_user
    if failed_imports:
        warning(f"{Fore.RED}Failed imports: {len(failed_imports)}{Style.RESET_ALL}")


def _print_configs(
    ctx_class: AppContext,
    system_folders: bool,
    running_service_names: list[str],
    instance_type: InstanceType,
) -> int:

    running = Fore.GREEN + "Running" + Style.RESET_ALL
    stopped = Fore.RED + "Not running" + Style.RESET_ALL

    configs, failed_imports = ctx_class.available_configurations(
        system_folders=system_folders
    )

    system_or_user = "System" if system_folders else "User  "
    system_or_user_lower = "system" if system_folders else "user"

    for config in configs:
        config.name = config.name.replace(SANDBOX_SUFFIX, "")
        status = (
            running
            if f"{APPNAME}-{config.name}-{system_or_user_lower}-{instance_type.value}"
            in running_service_names
            else stopped
        )
        click.echo(f"{config.name:25}{status:25}{system_or_user} ")

    return failed_imports
