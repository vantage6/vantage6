import click
import yaml
import os
import sys
import appdirs
import questionary as q
import errno

import vantage6.node.constants as constants

from pathlib import Path

from vantage6 import node
from vantage6.node import util
from vantage6.node.context import NodeContext
from vantage6.node.configuration.configuration_wizard import (
    configuration_wizard, 
    select_configuration_questionaire
)


@click.group(name="vantage6-node")
def cli_node():
    """Command `vantage6-node`."""
    pass

# 
#   list
#
import datetime
@cli_node.command(name="list")
def cli_node_list():
    """Lists all nodes in the default configuration directories."""
    
    click.echo("\nName"+(21*" ")+"Environments"+(21*" ")+"System/User")
    click.echo("-"*70)
    
    configs, f1 = NodeContext.available_configurations(system_folders=True)
    for config in configs:
        click.echo(f"{config.name:25}{str(config.available_environments):32} System ") 

    configs, f2 = NodeContext.available_configurations(system_folders=False)
    for config in configs:
        click.echo(f"{config.name:25}{str(config.available_environments):32} User   ") 

    click.echo("-"*70)
    click.echo(f"Number of failed imports: {len(f1)+len(f2)}")
#
#   new
#
@cli_node.command(name="new")
@click.option("-n", "--name", default=None)
@click.option('-e', '--environment', 
    default=constants.DEFAULT_NODE_ENVIRONMENT, 
    help='configuration environment to use'
)
@click.option('--system', 'system_folders', 
    flag_value=True
)
@click.option('--user', 'system_folders', 
    flag_value=False, 
    default=constants.DEFAULT_NODE_SYSTEM_FOLDERS
)
def cli_node_new_configuration(name, environment, system_folders):
    """Create a new configation file.
    
    Checks if the configuration already exists. If this is not the case
    a questionaire is invoked to create a new configuration file.
    """
    # select configuration name if none supplied
    if not name:
        name = q.text("Please enter a configuration-name:").ask()
    
    # check that this config does not exist
    if NodeContext.config_exists(name,environment,system_folders):
        raise FileExistsError(f"Configuration {name} and environment" 
            f"{environment} already exists!")

    # create config in ctx location
    cfg_file = configuration_wizard(name, environment=environment, 
        system_folders=system_folders)
    click.echo(f"New configuration created: {cfg_file}")

#
#   files
#
@cli_node.command(name="files")
@click.option("-n", "--name", 
    default=None, 
    help="configuration name"
)
@click.option('-e', '--environment', 
    default=constants.DEFAULT_NODE_ENVIRONMENT, 
    help='configuration environment to use'
)
@click.option('--system', 'system_folders', 
    flag_value=True
)
@click.option('--user', 'system_folders', 
    flag_value=False, 
    default=constants.DEFAULT_NODE_SYSTEM_FOLDERS
)
def cli_node_files(name, environment, system_folders):
    """Print out the paths of important files.
    
    If the specified configuration cannot be found, it exits. Otherwise
    it returns the absolute path to the output. 
    """
    # select configuration name if none supplied
    name, environment = (name, environment) if name else \
        select_configuration_questionaire('node', system_folders)
    
    # raise error if config could not be found
    if not NodeContext.config_exists(name,environment,system_folders):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), name)
    
    # create node context
    ctx = NodeContext(name,environment=environment, 
        system_folders=system_folders)

    # return path of the configuration
    click.echo(f"Configuration file = {ctx.config_file}")
    click.echo(f"Log file           = {ctx.log_file}")
    click.echo(f"data folders       = {ctx.data_dir}")
    click.echo(f"Database labels and files")
    for label, path in ctx.databases.items():
        click.echo(f" - {label:15} = {path}")

#
#   start
#
@cli_node.command(name='start')
@click.option("-n","--name", 
    default=None,
    help="configuration name"
)
@click.option("-c", "--config", 
    default=None, 
    help='absolute path to configuration-file; overrides NAME'
)
@click.option('-e', '--environment', 
    default=constants.DEFAULT_NODE_ENVIRONMENT, 
    help='configuration environment to use'
)
@click.option('--system', 'system_folders', 
    flag_value=True
)
@click.option('--user', 'system_folders', 
    flag_value=False, 
    default=constants.DEFAULT_NODE_SYSTEM_FOLDERS
)
def cli_node_start(name, config, environment, system_folders):
    """Start the node instance.
    
    If no name or config is specified the default.yaml configuation is used. 
    In case the configuration file not excists, a questionaire is
    invoked to create one. Note that in this case it is not possible to
    specify specific environments for the configuration (e.g. test, 
    prod, acc). 
    """
    
    # in case a configuration file is given, we by pass all the helper
    # stuff since you know what you are doing
    if config:
        ctx = NodeContext.from_external_config_file(config, environment, 
            system_folders)
    else:
        
        # in case no name is supplied, ask user to select one
        name, environment = (name, environment) if name \
            else select_configuration_questionaire(system_folders) 
                
        # check that config exists in the APP, if not a questionaire will
        # be invoked
        if not NodeContext.config_exists(name,environment,system_folders):
            if q.confirm(f"Configuration {name} using environment "
                f"{environment} does not exists. Do you want to create "
                f"this config now?").ask():
                configuration_wizard(name, environment=environment, 
                    system_folders=system_folders)
            else:
            
                sys.exit(0)
        
        # create dummy node context
        ctx = NodeContext(name, environment, system_folders)
        
    # run the node application
    node.run(ctx)