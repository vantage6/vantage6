import click

from vantage6.common import info
from vantage6.cli.context.server import ServerContext
from vantage6.cli.common.decorator import click_insert_context
from vantage6.common.globals import InstanceType


@click.command()
@click_insert_context(type_=InstanceType.ALGORITHM_STORE)
def cli_algo_store_files(ctx: ServerContext) -> None:
    """
    List files that belong to a particular server instance.
    """
    info(f"Configuration file = {ctx.config_file}")
    info(f"Log file           = {ctx.log_file}")
    info(f"Database           = {ctx.get_database_uri()}")
