from pathlib import Path
from shutil import rmtree

import click

from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.remove import execute_remove
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import InfraComponentName


@click.command()
@click.option(
    "-f", "--force", type=bool, flag_value=True, help="Don't ask for confirmation"
)
@click_insert_context(
    type_=InstanceType.NODE, include_name=True, include_system_folders=True
)
def cli_node_remove(
    ctx: NodeContext, name: str, system_folders: bool, force: bool
) -> None:
    """
    Delete a node permanently.

    Remove the configuration file, log file, and docker volumes attached to
    the node.
    """

    execute_remove(
        ctx, InstanceType.NODE, InfraComponentName.NODE, name, system_folders, force
    )

    # remove the folder: if it hasn't been started yet this won't exist...
    if Path.exists(ctx.config_dir / name):
        rmtree(ctx.config_dir / name)
