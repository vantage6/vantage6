from colorama import Fore, Style

from vantage6.common import ensure_config_dir_writable, error, info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import get_main_cli_command_name
from vantage6.cli.config import CliConfig
from vantage6.cli.configuration_wizard import configuration_wizard
from vantage6.cli.context import select_context_class
from vantage6.cli.utils import check_config_name_allowed, prompt_config_name


def new(
    name: str, system_folders: bool, namespace: str, context: str, type_: InstanceType
):
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
        if ctx_class.config_exists(name, system_folders):
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
        cfg_file = configuration_wizard(type_, name, system_folders)
    except KeyboardInterrupt:
        error("Configuration creation aborted.")
        exit(1)
    info(f"New configuration created: {Fore.GREEN}{cfg_file}{Style.RESET_ALL}")

    flag = "" if system_folders else "--user"
    info(
        f"You can start the {command_name} by running {Fore.GREEN}v6 {command_name} "
        f"start {flag}{Style.RESET_ALL}"
    )
