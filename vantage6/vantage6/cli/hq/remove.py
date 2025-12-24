import click

from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.remove import execute_remove
from vantage6.cli.context import HQContext
from vantage6.cli.globals import InfraComponentName


@click.command()
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(
    type_=InstanceType.HQ,
    include_name=True,
    include_system_folders=True,
    sandbox_param="sandbox",
)
@click.option("-f", "--force", "force", flag_value=True)
def cli_hq_remove(ctx: HQContext, name: str, system_folders: bool, force: bool) -> None:
    """
    Function to remove a HQ.

    Parameters
    ----------
    ctx : HQContext
        HQ context object
    force : bool
        Whether to ask for confirmation before removing or not
    """
    execute_remove(
        ctx, InstanceType.HQ, InfraComponentName.HQ, name, system_folders, force
    )
