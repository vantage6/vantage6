import click
import logging
import questionary as q
import IPython
import os
import errno
import yaml

# for shell python
import vantage.server.model as db

from functools import wraps
from pathlib import Path
from traitlets.config import get_config

from vantage.server.model.base import Database

from vantage import server, util, constants
from vantage.server import shell

from vantage.server.controller import fixture
from vantage.util.context import ( get_config_location, 
    select_configuration_questionaire, configuration_wizard ) 



def click_insert_context(func):

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
        default=constants.DEFAULT_SERVER_ENVIRONMENT,
        help='configuration environment to use'
    )
    @click.option('--system', 'system_folders', 
        flag_value=True
    )
    @click.option('--user', 'system_folders', 
        flag_value=False, 
        default=constants.DEFAULT_SERVER_SYSTEM_FOLDERS
    )
    @wraps(func)
    def func_with_context(name, config, environment, system_folders, 
        *args, **kwargs):
        
        # select configuration if none supplied
        if config:
            ctx = util.ServerContext.from_external_config_file(config,
                environment, system_folders)
        else:    
            name, environment = (name, environment) if name else \
                select_configuration_questionaire("server", system_folders)
            
            # raise error if config could not be found
            if not util.ServerContext.config_exists(name,environment, system_folders):
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), name)

            # create server context, and initialize db
            ctx = util.ServerContext(name,environment=environment, 
                system_folders=system_folders)
        Database().connect(ctx.get_database_uri())

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
@click_insert_context
def cli_server_start(ctx, ip, port, debug):
    """Start the server."""
    
    # Load the flask.Resources
    server.init_resources(ctx)
    
    # Run the server
    ip = ip or ctx.config['ip'] or '127.0.0.1'
    port = port or ctx.config['port'] or 5000
    server.run(ctx, ip, port, debug=debug)

#
#   list
#
@cli_server.command(name='list')
def cli_server_configuration_list():
    """Print the location of the default config file."""
    
    
    click.echo("\nName"+(21*" ")+"Environments"+(21*" ")+"System/User")
    click.echo("-"*70)
    
    sys_configs, f1 = util.ServerContext.available_configurations(system_folders=True)
    for config in sys_configs:
        click.echo(f"{config.name:25}{str(config.available_environments):32} System ") 

    usr_configs, f2 = util.ServerContext.available_configurations(system_folders=False)
    for config in usr_configs:
        click.echo(f"{config.name:25}{str(config.available_environments):32} User   ") 
    click.echo("-"*70)
    click.echo(f"Number of failed imports: {len(f1)+len(f2)}")

#
#   files
#
@cli_server.command(name='files')
@click_insert_context
def cli_server_files(ctx):
    """List file location of the server instance."""
    click.echo(f"Configuration file = {ctx.config_file}")
    click.echo(f"Log file           = {ctx.log_file}")
    click.echo(f"Database           = {ctx.get_database_uri()}")
    
#
#   new
#
@cli_server.command(name='new')
@click.option('-n','--name', 
    default=None,
    help="name of the configutation you want to use."
)
@click.option('-e', '--environment',
    default=constants.DEFAULT_SERVER_ENVIRONMENT,
    help='configuration environment to use'
)
@click.option('--system', 'system_folders', 
    flag_value=True
)
@click.option('--user', 'system_folders', 
    flag_value=False, 
    default=constants.DEFAULT_SERVER_SYSTEM_FOLDERS
)
def cli_server_new(name, environment, system_folders):
    """Create new configuration file."""

    if not name:
        name = q.text("Please enter a configuration-name:").ask()

    # check that this config does not exist
    if util.ServerContext.config_exists(name,environment,system_folders):
        raise FileExistsError(f"Configuration {name} and environment" 
            f"{environment} already exists!")

    # create config in ctx location
    cfg_file = configuration_wizard("server", name, environment=environment,
        system_folders=system_folders)
    click.echo(f"New configuration created: {cfg_file}")

#
#   import
#
@cli_server.command(name='import')
@click.argument('file_', type=click.Path(exists=True))
@click.option('--drop-all', is_flag=True, default=False)
@click_insert_context
def cli_server_import(ctx, file_, drop_all):
    """Import organizations/collaborations/users and tasks.
    
    Especially usefull for testing purposes.
    """
    
    with open(file_) as f:
        entities = yaml.safe_load(f.read())
    
    fixture.load(entities, drop_all=drop_all)

#
#   shell
#
@cli_server.command(name='shell')
@click_insert_context
def cli_server_shell(ctx):
    """Run a shell ..."""
    # shell.init(ctx.environment)
    c = get_config()
    c.InteractiveShellEmbed.colors = "Linux"
    IPython.embed(config=c)
