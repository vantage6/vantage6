import click

from subprocess import Popen, PIPE
from vantage6.common import info


@click.command()
def cli_node_attach() -> None:
    """
    Show the node logs in the current console.
    """
    info("Attaching to node logs...")

    command = ["devspace", "logs", "--follow", "--label-selector", "app=node"]
    process = Popen(command, stdout=None, stderr=None)  # Redirecting output to the terminal
    process.wait()  # Wait for the process to complete
