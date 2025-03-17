import click

from vantage6.common import info
from vantage6.cli.common.utils import attach_logs


@click.command()
def cli_server_attach() -> None:
    """
    Show the server logs in the current console.
    """
    info("Attaching to server logs...")
    attach_logs("app=vantage6-server", "component=vantage6-server")
