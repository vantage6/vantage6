import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context.hq import HQContext


@click.command()
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(type_=InstanceType.HQ, sandbox_param="sandbox")
def cli_hq_files(ctx: HQContext) -> None:
    """
    List files that belong to a particular HQ instance.
    """
    info(f"Configuration file = {ctx.config_file}")
    info(f"Log file           = {ctx.log_file}")
    info(f"Database           = {ctx.get_database_uri()}")
