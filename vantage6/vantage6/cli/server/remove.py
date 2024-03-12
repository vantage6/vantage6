import itertools
import click
import questionary as q

from vantage6.common import info
from vantage6.common.docker.addons import check_docker_running
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context import ServerContext
from vantage6.cli.utils import remove_file


@click.command()
@click_insert_context(type_="server")
@click.option("-f", "--force", "force", flag_value=True)
def cli_server_remove(ctx: ServerContext, force: bool) -> None:
    """
    Function to remove a server.

    Parameters
    ----------
    ctx : ServerContext
        Server context object
    force : bool
        Whether to ask for confirmation before removing or not
    """
    check_docker_running()

    if not force:
        if not q.confirm(
            "This server will be deleted permanently including its "
            "configuration. Are you sure?",
            default=False,
        ).ask():
            info("Server will not be deleted")
            exit(0)

    # now remove the folders...
    remove_file(ctx.config_file, "configuration")

    for handler in itertools.chain(ctx.log.handlers, ctx.log.root.handlers):
        handler.close()
    remove_file(ctx.log_file, "log")
