import click

from pytaskmanager.cli import node, server


@click.group()
def cli():
    """Main entry point for CLI scripts."""
    pass


# ptm node <command>
cli.add_command(node.cli_node)

# ptm server <command>
cli.add_command(server.cli_server)
