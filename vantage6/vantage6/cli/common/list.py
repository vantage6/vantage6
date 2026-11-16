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


def get_configuration_list(
    instance_type: InstanceType,
    query_helm: bool = True,
    other_running: list[str] | None = None,
    show_runtime: bool = False,
) -> None:
    """
    Print list of available configurations.

    Parameters
    ----------
    instance_type : InstanceType
        The type of instance to get the configurations for
    query_helm : bool
        Whether to ask Helm which instances run
    other_running : list[str] | None
        Names of instances that run elsewhere, e.g. with Docker
    show_runtime : bool
        Whether to show where each instance runs
    """
    ctx_class = select_context_class(instance_type)

    running_service_names = list(other_running or [])
    if query_helm:
        running_service_names += find_running_service_names(instance_type)
    header = "\nName" + (21 * " ") + "Status" + (10 * " ") + "System/User"
    if show_runtime:
        header += (2 * " ") + "Runtime"

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
            show_runtime=show_runtime,
        )
    else:
        failed_imports_system = _print_configs(
            ctx_class=ctx_class,
            system_folders=True,
            running_service_names=running_service_names,
            instance_type=instance_type,
            show_runtime=show_runtime,
        )
        failed_imports_user = _print_configs(
            ctx_class=ctx_class,
            system_folders=False,
            running_service_names=running_service_names,
            instance_type=instance_type,
            show_runtime=show_runtime,
        )
        failed_imports = failed_imports_system + failed_imports_user

    click.echo("-" * len(header))
    if failed_imports:
        warning(f"{Fore.RED}Failed imports: {len(failed_imports)}{Style.RESET_ALL}")


def _print_configs(
    ctx_class: AppContext,
    system_folders: bool,
    running_service_names: list[str],
    instance_type: InstanceType,
    show_runtime: bool = False,
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
        line = f"{config.name:25}{status:25}{system_or_user} "
        if show_runtime:
            runtime = None
            if isinstance(config.config, dict):
                runtime = config.config.get("runtime")
            line += f" {runtime or 'kubernetes'}"
        click.echo(line)

    return failed_imports
