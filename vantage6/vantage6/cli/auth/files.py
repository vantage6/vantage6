import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context.auth import AuthContext


@click.command()
@click_insert_context(type_=InstanceType.AUTH)
def cli_auth_files(ctx: AuthContext) -> None:
    """
    List files that belong to a particular auth instance.
    """
    info(f"Configuration file = {ctx.config_file}")
