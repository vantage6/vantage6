import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext


@click.command()
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(type_=InstanceType.ALGORITHM_STORE, sandbox_param="sandbox")
def cli_algo_store_files(ctx: AlgorithmStoreContext) -> None:
    """
    List files that belong to a particular algorithm store instance.
    """
    info(f"Configuration file = {ctx.config_file}")
    info(f"Log file           = {ctx.log_file}")
    info(f"Database           = {ctx.get_database_uri()}")
