from pathlib import Path

from colorama import Fore, Style

from vantage6.common import ensure_config_dir_writable, error, info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import get_main_cli_command_name
from vantage6.cli.config import CliConfig
from vantage6.cli.configuration_create import make_configuration
from vantage6.cli.context import select_context_class
from vantage6.cli.utils import check_config_name_allowed, prompt_config_name


def new(
    config_producing_func: callable,
    config_producing_func_args: tuple,
    name: str,
    system_folders: bool,
    namespace: str,
    context: str,
    type_: InstanceType,
    is_sandbox: bool = False,
) -> Path | None:
    """
    Create a new configuration.

    Parameters
    ----------
    config_producing_func : callable
        Function to generate the configuration
    config_producing_func_args : tuple
        Arguments to pass to the config producing function
    name : str
        Name of the configuration
    system_folders : bool
        Whether to store the configuration in the system folders
    namespace : str
        Namespace to use
    context : str
        Context to use
    type_ : InstanceType
        Type of the configuration (node, server, algorithm store, etc)
    is_sandbox : bool
        Whether to create a sandbox configuration or not

    Returns
    -------
    Path | None
        Path to the configuration file. None if the process is aborted for any reason.
    """
    cli_config = CliConfig()
    context, namespace = cli_config.compare_changes_config(
        context=context,
        namespace=namespace,
    )

    name = prompt_config_name(name)

    # check if name is valid
    check_config_name_allowed(name)

    # check that this config does not exist
    ctx_class = select_context_class(type_)
    try:
        if ctx_class.config_exists(name, system_folders, is_sandbox):
            error(f"Configuration {Fore.RED}{name}{Style.RESET_ALL} already exists!")
            exit(1)
    except Exception as e:
        error(e)

        exit(1)

    command_name = get_main_cli_command_name(type_)

    # Check that we can write in this folder
    if not ensure_config_dir_writable(system_folders):
        error("Your user does not have write access to all folders. Exiting")
        info(
            f"Create a new {command_name} using '{Fore.GREEN}v6 {command_name} new "
            f"--user{Style.RESET_ALL}' instead!"
        )
        exit(1)

    # create config in ctx location
    try:
        cfg_file = make_configuration(
            config_producing_func=config_producing_func,
            config_producing_func_args=config_producing_func_args,
            type_=type_,
            instance_name=name,
            system_folders=system_folders,
            is_sandbox=is_sandbox,
        )
    except KeyboardInterrupt:
        error("Configuration creation aborted.")
        exit(1)
    info(f"New configuration created: {Fore.GREEN}{cfg_file}{Style.RESET_ALL}")

    flag = "" if system_folders else "--user"
    info(
        f"You can start the {command_name} by running {Fore.GREEN}v6 {command_name} "
        f"start {flag}{Style.RESET_ALL}"
    )
    return cfg_file
