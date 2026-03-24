import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context.hub import HubContext


@click.command()
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(type_=InstanceType.HUB, sandbox_param="sandbox")
def cli_hub_files(ctx: HubContext) -> None:
    """
    List files that belong to a particular HQ instance.
    """
    info(f"Configuration file = {ctx.config_file}")
    # TODO extend with log files / database URLs of HQ / Store / Auth ??
