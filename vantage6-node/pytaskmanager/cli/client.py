import click
import yaml

from pytaskmanager import util, client
from pytaskmanager.util.find_files import get_config_location

APPNAME = 'pytaskmanager'


# ------------------------------------------------------------------------------
# helper functions
# ------------------------------------------------------------------------------


def set_api_key_in_client_config(cfg_filename, api_key=None):
    """"Make sure an API is present in the client configuration file"""

    with open(cfg_filename, 'r') as f:
        config = yaml.load(f)

    # get the api key from the config file, this could be an empty field
    config_api_key = config['application']['api_key']

    # check if api-key is not set in the config file and not provided
    if not config_api_key and not api_key:
        api_key = click.prompt("please enter API-key", type=str)

    if api_key:

        config['application']['api_key'] = api_key

        with open(cfg_filename, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)


# ------------------------------------------------------------------------------
# ptm client
# ------------------------------------------------------------------------------
@click.group(name='client')
def cli_client():
    """Subcommand `ptm client`."""
    pass


@cli_client.command(name='config_location')
@click.option('-n', '--name', default='default', help='client instance to use')
def cli_server_configlocation(name):
    """Print the location of the default config file."""
    ctx = util.AppContext(APPNAME, 'client', name)
    cfg_filename = get_config_location(ctx, config=None, force_create=False)
    click.echo('{}'.format(cfg_filename))


@cli_client.command(name='start')
@click.option('-n', '--name', default='default', help='client instance to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
@click.option('-a', '--api_key', default=None, help='ptm server api-key')
def cli_client_start(name, config, api_key):
    """Start the client."""
    ctx = util.AppContext(APPNAME, 'client', name)

    # Load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create=False)

    # provide api key to the configuration file
    set_api_key_in_client_config(cfg_filename, api_key)

    ctx.init(cfg_filename)

    # Run the client
    client.run(ctx)
