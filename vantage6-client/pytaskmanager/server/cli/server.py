import click
import logging
import questionary as q

from functools import wraps
from pathlib import Path

from pytaskmanager import server, util, APPNAME
from pytaskmanager.server import db, shell, fixtures
from pytaskmanager.util.context import get_config_location, select_configuration_questionaire

# ------------------------------------------------------------------------------
# context decorator
# see: https://github.com/pallets/click/issues/108
# ------------------------------------------------------------------------------
# TODO do we need the force_create to be an option too?
def set_context(return_context=True):
    def real_set_context(func):

        # add option decorators
        @click.argument('name', 
            default=None
        )
        @click.option('-c', '--config', 
            default=None, 
            help='absolute path to configuration-file; overrides NAME'
        )
        @click.option('-e', '--environment',
            default=None,
            help='database environment to use'
        )
        @wraps(func)
        def func_with_context(name, config, environment, *args, **kwargs):
            
            # select configuration if none supplied
            name = name if name else \
                select_configuration_questionaire("server")
            
            # empty server context
            ctx = util.ServerContext(APPNAME, name)

            # check if configuration exists
            cfg_file = config if config else ctx.config_file
            if not Path(cfg_file).exists():
                click.echo(f"Configuration file {cfg_file} does not exist.")
                if q.confirm("Do you want to create this config now?"):
                    ### TODO 08-03 this is where you left!
                    pass

            # load configuration and initialize logging system
            cfg_filename = get_config_location(ctx, config, force_create=False)
            ctx.init(cfg_filename, environment)

            # initialize database from environment
            uri = ctx.get_database_location()
            db.init(uri)

            if return_context:
                return func(ctx, *args, **kwargs)
            else:
                return func(*args, **kwargs)

        return func_with_context
    return real_set_context


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
@set_context()
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
    ctx = util.AppContext(APPNAME, 'server', name)
    cfg_filename = get_config_location(ctx, config=None, force_create=False)
    click.echo('{}'.format(cfg_filename))

#
#   import
#
@cli_server.command(name='load_fixtures')
@set_context()
def cli_server_load_fixtures(ctx):
    """Load fixtures for testing."""
    fixtures.init(ctx)
    fixtures.create()

#
#   shell
#
@cli_server.command(name='shell')
@set_context()
def cli_server_shell(ctx):
    """Run a shell ..."""
    # shell.init(ctx.environment)
    import IPython
    from traitlets.config import get_config
    c = get_config()
    c.InteractiveShellEmbed.colors = "Linux"

    IPython.embed(config=c)
