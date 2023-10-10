import click

from vantage6.cli.dev.cli import cli_dev
from vantage6.cli.node.cli import cli_node
from vantage6.cli.server.cli import cli_server


@click.group(name='cli')
def cli_complete() -> None:
    """
    The `v6` command line interface allows you to manage your vantage6
    infrastructure.
    It provides a number of subcommands to help you with this task.
    """


cli_complete.add_command(cli_node)
cli_complete.add_command(cli_server)
cli_complete.add_command(cli_dev)
