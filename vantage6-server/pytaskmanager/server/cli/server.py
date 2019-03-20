import click
import logging
import questionary as q
import IPython
import os
import errno

from functools import wraps
from pathlib import Path
from traitlets.config import get_config

from pytaskmanager import server, util, settings, APPNAME
from pytaskmanager.server import db, shell, fixtures
from pytaskmanager.util.context import get_config_location, select_configuration_questionaire

# ------------------------------------------------------------------------------
# context decorator
# see: https://github.com/pallets/click/issues/108
# ------------------------------------------------------------------------------
# TODO do we need the force_create to be an option too?
def set_context(func):

    # add option decorators
    @click.option('-n','--name', 
        default=None,
        help="name of the configutation you want to use."
    )
    @click.option('-c', '--config', 
        default=None, 
        help='absolute path to configuration-file; overrides NAME'
    )
    @click.option('-e', '--environment',
        default=settings.DEFAULT_SERVER_ENVIRONMENT,
        help='configuration environment to use'
    )
    @click.option('--system', 'system_folders', 
        flag_value=True
    )
    @click.option('--user', 'system_folders', 
        flag_value=False, 
        default=settings.DEFAULT_SERVER_SYSTEM_FOLDERS
    )
    @wraps(func)
    def func_with_context(name, config, environment, system_folders, *args, **kwargs):
        
        # select configuration if none supplied
        name, environment = (name, environment) if name else \
            select_configuration_questionaire("server", system_folders)
        
        # raise error if config could not be found
        if not util.ServerContext.config_exists(name,environment, system_folders):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), name)

        # create server context, and initialize db
        ctx = util.ServerContext(name,environment=environment, 
            system_folders=system_folders)
        db.init(ctx.get_database_uri())

        return func(ctx, *args, **kwargs)
        
    return func_with_context


@click.group(name='server')
def cli_server():
    """Subcommand `ptm server`."""
    pass

#
#   start
#
@cli_server.command(name='start')
@click.option('--ip', default=None, help='ip address to listen on')
@click.option('-p', '--port', type=int, help='port to listen on')
@click.option('--debug', is_flag=True, help='run server in debug mode (auto-restart)')
@set_context
def cli_server_start(ctx, ip, port, debug):
    """Start the server."""
    
    # Load the flask.Resources
    server.init_resources(ctx)
    
    # Run the server
    ip = ip or ctx.config['ip'] or '127.0.0.1'
    port = port or ctx.config['port'] or 5000
    server.run(ctx, ip, port, debug=debug)

#
#   files
#
@cli_server.command(name='config_location')
@click.option('-n', '--name', default='default', help='server instance to use')
def cli_server_configlocation(name):
    """Print the location of the default config file."""
    ctx = util.ServerContext(name,"test", False)
    cfg_filename = get_config_location(ctx, config=None, force_create=False)
    click.echo('{}'.format(cfg_filename))

#
#   import
#
@cli_server.command(name='load_fixtures')
@set_context
def cli_server_load_fixtures(ctx):
    """Load fixtures for testing."""
    fixtures.init(ctx)
    fixtures.create()

#
#   shell
#
@cli_server.command(name='shell')
@set_context
def cli_server_shell(ctx):
    """Run a shell ..."""
    # shell.init(ctx.environment)
    c = get_config()
    c.InteractiveShellEmbed.colors = "Linux"
    IPython.embed(config=c)
