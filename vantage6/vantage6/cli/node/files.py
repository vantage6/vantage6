import click

from vantage6.common import info
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
from vantage6.cli.node.common import select_node


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Search for the configuration in the system folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Search for the configuration in the user folders. This is " "the default",
)
def cli_node_files(name: str, system_folders: bool) -> None:
    """
    Prints the location of important node files.

    If the specified configuration cannot be found, it exits. Otherwise
    it returns the absolute path to the output.
    """
    name = select_node(name, system_folders)

    # create node context
    ctx = NodeContext(name, system_folders=system_folders)

    # return path of the configuration
    info(f"Configuration file = {ctx.config_file}")
    info(f"Log file           = {ctx.log_file}")
    info(f"data folders       = {ctx.data_dir}")
    info("Database labels and files")
    for db in ctx.databases:
        info(f" - {db['label']:15} = {db['uri']} (type: {db['type']})")
