import click

from pytaskmanager.cli import client, server


@click.group()
def cli():
    """Main entry point for CLI scripts."""
    pass


# ptm client <command>
cli.add_command(client.cli_client)

# ptm server <command>
cli.add_command(server.cli_server)
