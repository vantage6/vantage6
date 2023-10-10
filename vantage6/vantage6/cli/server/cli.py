"""
The server module contains the CLI commands for the server manager. The
following commands are available:

    * vserver new
    * vserver list
    * vserver start
    * vserver stop
    * vserver files
    * vserver import
    * vserver attach
    * vserver version
    * vserver shell
"""
import click

from vantage6.cli.server.attach import cli_server_attach
from vantage6.cli.server.files import cli_server_files
from vantage6.cli.server.import_ import cli_server_import
from vantage6.cli.server.list import cli_server_configuration_list
from vantage6.cli.server.new import cli_server_new
from vantage6.cli.server.shell import cli_server_shell
from vantage6.cli.server.start import cli_server_start
from vantage6.cli.server.stop import cli_server_stop
from vantage6.cli.server.version import cli_server_version


@click.group(name='server')
def cli_server() -> None:
    """
    The `vserver` commands allow you to manage your vantage6 server instances.
    """


cli_server.add_command(cli_server_attach, name='attach')
cli_server.add_command(cli_server_files, name='files')
cli_server.add_command(cli_server_import, name='import')
cli_server.add_command(cli_server_configuration_list, name='list')
cli_server.add_command(cli_server_new, name='new')
cli_server.add_command(cli_server_shell, name='shell')
cli_server.add_command(cli_server_start, name='start')
cli_server.add_command(cli_server_stop, name='stop')
cli_server.add_command(cli_server_version, name='version')
