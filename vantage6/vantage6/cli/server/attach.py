import click

from subprocess import Popen, PIPE
from vantage6.common import info


@click.command()
def cli_server_attach() -> None:
    """
    Show the server logs in the current console.
    """
    info("Attaching to server logs...")

    command = [
        "devspace",
        "logs",
        "--follow",
        "--label-selector",
        "app=vantage6-server",
        "--label-selector",
        "component=vantage6-server",
    ]
    process = Popen(command, stdout=None, stderr=None)
    process.wait()
