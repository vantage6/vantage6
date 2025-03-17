import click

from vantage6.common import info
from vantage6.cli.common.utils import attach_logs


@click.command()
def cli_node_attach() -> None:
    """
    Show the node logs in the current console.
    """
    info("Attaching to node logs...")
    attach_logs("app=node")
