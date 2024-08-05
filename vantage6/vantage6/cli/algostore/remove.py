import itertools
from pathlib import Path
from shutil import rmtree
import click
import questionary as q

from vantage6.common import info
from vantage6.common.docker.addons import check_docker_running
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context import AlgorithmStoreContext
from vantage6.cli.utils import remove_file
from vantage6.common.globals import InstanceType


@click.command()
@click_insert_context(type_=InstanceType.ALGORITHM_STORE)
@click.option("-f", "--force", "force", flag_value=True)
def cli_algo_store_remove(ctx: AlgorithmStoreContext, force: bool) -> None:
    """
    Function to remove an algorithm store.

    Parameters
    ----------
    ctx : AlgorithmStoreContext
        Algorithm store context object
    force : bool
        Whether to ask for confirmation before removing or not
    """
    check_docker_running()

    if not force:
        if not q.confirm(
            "This algorithm store will be deleted permanently including its "
            "configuration. Are you sure?",
            default=False,
        ).ask():
            info("Algorithm store will not be deleted")
            exit(0)

    # now remove the folders...
    remove_file(ctx.config_file, "configuration")

    # ensure log files are closed before removing
    log_dir = Path(ctx.log_file.parent)
    info(f"Removing log directory: {log_dir}")
    for handler in itertools.chain(ctx.log.handlers, ctx.log.root.handlers):
        handler.close()
    # remove the whole folder with all the log files (if it exists)
    try:
        rmtree(log_dir)
    except FileNotFoundError:
        pass
