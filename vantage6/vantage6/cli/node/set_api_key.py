import click
import questionary as q

from vantage6.common import error, info, ensure_config_dir_writable
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
from vantage6.cli.configuration_wizard import NodeConfigurationManager
from vantage6.cli.node.common import select_node


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--api-key", default=None, help="New API key")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Search for configuration in system folders rather than " "user folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Search for configuration in user folders rather than "
    "system folders. This is the default",
)
def cli_node_set_api_key(name: str, api_key: str, system_folders: bool) -> None:
    """
    Put a new API key into the node configuration file
    """
    # select node name
    name = select_node(name, system_folders)

    # Check that we can write in the config folder
    if not ensure_config_dir_writable(system_folders):
        error("Your user does not have write access to all folders. Exiting")
        exit(1)

    if not api_key:
        try:
            api_key = q.text("Please enter your new API key:").unsafe_ask()
        except KeyboardInterrupt:
            error("API key input aborted.")
            exit(1)

    # get configuration manager
    ctx = NodeContext(name, system_folders=system_folders)
    conf_mgr = NodeConfigurationManager.from_file(ctx.config_file)

    # set new api key, and save the file
    ctx.config["api_key"] = api_key
    conf_mgr.put(ctx.config)
    conf_mgr.save(ctx.config_file)
    info("Your new API key has been uploaded to the config file " f"{ctx.config_file}.")
