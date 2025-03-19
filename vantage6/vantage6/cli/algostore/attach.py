import click

from vantage6.common import info
from vantage6.cli.common.utils import attach_logs


@click.command()
def cli_algo_store_attach() -> None:
    """
    Show the store logs in the current console.
    """
    info("Attaching to store logs...")
    attach_logs("app=store", "component=store-server")
