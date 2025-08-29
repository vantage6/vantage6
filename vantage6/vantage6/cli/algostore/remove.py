import click

from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.remove import execute_remove
from vantage6.cli.context import AlgorithmStoreContext
from vantage6.cli.globals import InfraComponentName


@click.command()
@click_insert_context(
    type_=InstanceType.ALGORITHM_STORE, include_name=True, include_system_folders=True
)
@click.option("-f", "--force", "force", flag_value=True)
def cli_algo_store_remove(
    ctx: AlgorithmStoreContext, name: str, system_folders: bool, force: bool
) -> None:
    """
    Function to remove an algorithm store.

    Parameters
    ----------
    ctx : AlgorithmStoreContext
        Algorithm store context object
    force : bool
        Whether to ask for confirmation before removing or not
    """
    execute_remove(
        ctx,
        InstanceType.ALGORITHM_STORE,
        InfraComponentName.ALGORITHM_STORE,
        name,
        system_folders,
        force,
    )
