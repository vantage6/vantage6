import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context.node import NodeContext


@click.command()
@click_insert_context(type_=InstanceType.NODE)
def cli_node_files(ctx: NodeContext) -> None:
    """
    Prints the location of important node files.

    If the specified configuration cannot be found, it exits. Otherwise
    it returns the absolute path to the output.
    """
    info(f"Configuration file = {ctx.config_file}")
    info(f"Log file           = {ctx.log_file}")
    info(f"data folders       = {ctx.data_dir}")
    info("Database labels and files")
    for db in ctx.databases["fileBased"] or []:
        info(
            f" - {db['name']:15} = {db['volumePath']}/{db['originalName']} "
            f"(type: {db['type']})"
        )
    for db in ctx.databases["serviceBased"] or []:
        info(f" - {db['name']:15} = {db['uri']} (type: {db['type']})")
