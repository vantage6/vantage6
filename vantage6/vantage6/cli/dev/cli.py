"""
This module contains the CLI commands for generating dummy server and node
instance(s). The following commands are available:

    * vdev create-demo-network
    * vdev remove-demo-network
    * vdev start-demo-network
    * vdev stop-demo-network
"""
import click

from vantage6.cli.dev.create import create_demo_network
from vantage6.cli.dev.remove import remove_demo_network
from vantage6.cli.dev.start import start_demo_network
from vantage6.cli.dev.stop import stop_demo_network


@click.group(name="dev")
def cli_dev() -> None:
    """
    The `vdev` commands can be used to quickly manage a network with a server
    and several nodes for local testing.
    """


cli_dev.add_command(create_demo_network, name="create-demo-network")
cli_dev.add_command(remove_demo_network, name="remove-demo-network")
cli_dev.add_command(start_demo_network, name="start-demo-network")
cli_dev.add_command(stop_demo_network, name="stop-demo-network")
