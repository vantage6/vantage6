import click
from colorama import Fore, Style

from vantage6.common import error, info, ensure_config_dir_writable
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
from vantage6.cli.configuration_wizard import configuration_wizard
from vantage6.cli.utils import check_config_name_allowed, prompt_config_name
from vantage6.common.globals import InstanceType


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Store this configuration in the system folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Store this configuration in the user folders. This is the " "default",
)
def cli_node_new_configuration(name: str, system_folders: bool) -> None:
    """
    Create a new node configuration.

    Checks if the configuration already exists. If this is not the case
    a questionnaire is invoked to create a new configuration file.
    """
    name = prompt_config_name(name)
    # check if config name is allowed docker name
    check_config_name_allowed(name)

    # check that this config does not exist
    if NodeContext.config_exists(name, system_folders):
        error(f"Configuration {name} already exists!")
        exit(1)

    # Check that we can write in this folder
    if not ensure_config_dir_writable(system_folders):
        error("Cannot write configuration file. Exiting...")
        exit(1)

    # create config in ctx location
    flag = "--system" if system_folders else ""
    try:
        cfg_file = configuration_wizard(InstanceType.NODE, name, system_folders)
    except KeyboardInterrupt:
        error("Configuration creation aborted.")
        exit(1)
    info(f"New configuration created: {Fore.GREEN}{cfg_file}{Style.RESET_ALL}")
    info(
        f"You can start the node by running "
        f"{Fore.GREEN}v6 node start {flag}{Style.RESET_ALL}"
    )
