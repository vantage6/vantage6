import click

from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.remove import execute_remove
from vantage6.cli.context import ServerContext
from vantage6.cli.globals import InfraComponentName


@click.command()
@click_insert_context(
    type_=InstanceType.SERVER, include_name=True, include_system_folders=True
)
@click.option("-f", "--force", "force", flag_value=True)
def cli_server_remove(
    ctx: ServerContext, name: str, system_folders: bool, force: bool
) -> None:
    """
    Function to remove a server.

    Parameters
    ----------
    ctx : ServerContext
        Server context object
    force : bool
        Whether to ask for confirmation before removing or not
    """
    execute_remove(
        ctx, InstanceType.SERVER, InfraComponentName.SERVER, name, system_folders, force
    )
