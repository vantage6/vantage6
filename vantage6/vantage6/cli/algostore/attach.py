import click

from subprocess import Popen, PIPE
from vantage6.common import info


@click.command()
def cli_server_attach() -> None:
    """
    Show the store logs in the current console.
    """
    info("Attaching to store logs...")

    command = [
        "devspace",
        "logs",
        "--follow",
        "--label-selector",
        "app=store, component=store-server",
    ]
    process = Popen(command, stdout=None, stderr=None)
    process.wait()
