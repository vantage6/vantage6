import click

import sys, os
import shutil
import yaml
import logging

import appdirs

# Define version and directories *before* importing submodules
here = os.path.abspath(os.path.dirname(__file__))

__version__ = ''

with open(os.path.join(here, 'VERSION')) as fp:
    __version__ = fp.read()


# default parameters for click.Path
pparams = {
    'exists': False, 
    'file_okay': False, 
    'dir_okay': True,
}

from . import server
from .server import fixtures
from .server import db
from . import client
from . import utest
from . import util

APPNAME = 'pytaskmanager'

# ------------------------------------------------------------------------------
# helper functions
# ------------------------------------------------------------------------------
def get_config_location(ctx, config, force_create):
    """Ensure configuration file exists and return its location."""
    if config is None:
        # Get the location of config.yaml if not provided
        filename = ctx.config_file
    else:
        # Use the config file provided as argument
        filename = config

    # Check that the config file exists and create it if necessary, but
    # only if it was not explicitly provided!
    if not os.path.exists(filename):
        # We will always create a configuration file at the default location
        # when necessary.
        if config and not force_create:
            click.echo("Configuration file '{}' does not exist and '--force-create' not specified!".format(filename))
            click.echo("Aborting ...")
            sys.exit(1)

        # Make sure the directory exists
        dirname = os.path.dirname(filename)

        if dirname:
            os.makedirs(dirname, exist_ok=True)

        # Copy a default config file
        if ctx.instance_type == 'server':
            skeleton_file = 'server_config_skeleton.yaml'
        elif ctx.instance_type == 'client':
            skeleton_file = 'client_config_skeleton.yaml'
        elif ctx.instance_type == 'unittest':
            skeleton_file = 'unittest_config_skeleton.yaml'

        src = os.path.join(here, '_data', skeleton_file)
        dst = os.path.join(filename)
        shutil.copy(src, dst)

        if ctx.instance_type == 'server':
            with open(dst, 'r') as fp:
                cfg = yaml.load(fp)
                print('-' * 80)
                print(cfg)
                print('-' * 80)

            cfg['application']['logging']['file'] = ctx.instance_name +'.log'

            with open(dst, 'w') as fp:
                yaml.dump(cfg, fp)

    return filename


@click.group()
def cli():
    """Main entry point for CLI scripts."""
    pass


# ------------------------------------------------------------------------------
# ptm test
# ------------------------------------------------------------------------------
@cli.command(name='test')
@click.option('-c', '--config', default=None, type=click.Path(), help='location of the config file')
def cli_test(config):
    """Run unit tests."""
    ctx = util.AppContext(APPNAME, 'unittest')
    cfg_filename = get_config_location(ctx, config=None, force_create=False)
    ctx.init(cfg_filename)
    utest.run()


# ------------------------------------------------------------------------------
# ptm server
# ------------------------------------------------------------------------------
@cli.group(name='server')
def cli_server():
    """Subcommand `ptm server`."""
    pass


@cli_server.command(name='start')
@click.option('-n', '--name', default='default', help='server instance to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('--ip', default='0.0.0.0', help='ip address to listen on')
@click.option('-p', '--port', default=5000, help='port to listen on')
@click.option('--debug/--no-debug', default=True, help='run server in debug mode (auto-restart)')
@click.option('--force-create', is_flag=True, help='Force creation of config file')
def cli_server_start(name, config, environment, ip, port, debug, force_create):
    """Start the server."""
    click.echo("Starting server ...")
    ctx = util.AppContext(APPNAME, 'server', name)

    # Load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create)
    ctx.init(cfg_filename, environment)

    # Load the flask.Resources
    server.init_resources(ctx)
    # Run the server
    server.run(ctx, ip, port, debug=debug)


@cli_server.command(name='config_location')
@click.option('-n', '--name', default='default', help='server instance to use')
def cli_server_configlocation(name):
    """Print the location of the default config file."""
    ctx = util.AppContext(APPNAME, 'server', name)
    cfg_filename = get_config_location(ctx, config=None, force_create=False)
    click.echo('{}'.format(cfg_filename))


@cli_server.command(name='passwd')
@click.option('-n', '--name', default='default', help='server instance to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('-p', '--password', prompt='Password', hide_input=True)
def cli_server_passwd(name, config, environment, password):
    """Set the root password."""
    log = logging.getLogger('ptm')


    ctx = util.AppContext(APPNAME, 'server', name)

    # Load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create)
    ctx.init(cfg_filename, environment)

    uri = ctx.get_database_location()
    db.init(uri)

    try:
        root = db.User.getByUsername('root')
    except Exception as e:
        log.info("Creating user root")        
        root = db.User(username='root')

    log.info("Setting password for root")
    root.set_password(password)
    root.save()

    log.info("[DONE]")



@cli_server.command(name='load_fixtures')
@click.option('-n', '--name', default='default', help='server instance to use')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
def cli_server_load_fixtures(name, environment, config):
    """Load fixtures for testing."""
    click.echo("Loading fixtures.")
    ctx = util.AppContext(APPNAME, 'server', name)

    # Load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create=False)
    ctx.init(cfg_filename, environment)

    fixtures.init(ctx)
    fixtures.create()


# ------------------------------------------------------------------------------
# ptm client
# ------------------------------------------------------------------------------
@cli.group(name='client')
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
def cli_client_start(name, config):
    """Start the client."""
    ctx = util.AppContext(APPNAME, 'client', name)

    # Load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create=False)
    ctx.init(cfg_filename)

    # Run the client
    client.run(ctx)




