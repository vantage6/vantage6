"""
The node module contains the CLI commands for the node manager. The following
commands are available:

    * vnode new
    * vnode list
    * vnode files
    * vnode start
    * vnode stop
    * vnode attach
    * vnode clean
    * vnode remove
    * vnode version
    * vnode create-private-key
"""
import click

from vantage6.cli.node.attach import cli_node_attach
from vantage6.cli.node.clean import cli_node_clean
from vantage6.cli.node.create_private_key import cli_node_create_private_key
from vantage6.cli.node.files import cli_node_files
from vantage6.cli.node.list import cli_node_list
from vantage6.cli.node.new import cli_node_new_configuration
from vantage6.cli.node.remove import cli_node_remove
from vantage6.cli.node.set_api_key import cli_node_set_api_key
from vantage6.cli.node.start import cli_node_start
from vantage6.cli.node.stop import cli_node_stop
from vantage6.cli.node.version import cli_node_version


@click.group(name="node")
def cli_node() -> None:
    """
    The `vnode` commands allow you to manage your vantage6 node instances.
    """


cli_node.add_command(cli_node_attach, name="attach")
cli_node.add_command(cli_node_clean, name="clean")
cli_node.add_command(cli_node_create_private_key, name="create-private-key")
cli_node.add_command(cli_node_files, name="files")
cli_node.add_command(cli_node_list, name="list")
cli_node.add_command(cli_node_new_configuration, name="new")
cli_node.add_command(cli_node_remove, name="remove")
cli_node.add_command(cli_node_set_api_key, name="set-api-key")
cli_node.add_command(cli_node_start, name="start")
cli_node.add_command(cli_node_stop, name="stop")
cli_node.add_command(cli_node_version, name="version")
