import click
import yaml
import os
import sys
import questionary as q

from pathlib import Path

from pytaskmanager import util, node, APPNAME
from pytaskmanager.util.context import (
    configuration_wizard, select_configuration_questionaire)


@click.group(name="node")
def cli_node():
    """Subcommand `ppdli node`."""
    pass

# 
#   list
#
@cli_node.command(name="list")
def cli_node_list():
    """Lists all nodes in the default configuration directory."""
    ctx = util.NodeContext(APPNAME)
    files = Path(ctx.config_dir).glob("*.yaml")
    click.echo("Node instances")
    [click.echo(f" - {file_.stem}") for file_ in files]

#
#   new
#
@cli_node.command(name="new")
@click.argument("name", default=None, required=False)
def cli_node_new_configuration(name):
    """Create a new configation file.
    
    Checks if the configuration already exists. If this is not the case
    a questionaire is invoked to create a new configuration file.
    """
    name = name if name else q.text("Choice configuration name:").ask()

    # create dummy node context
    ctx = util.NodeContext(APPNAME, name)

    # check that this config does not exist
    if ctx.config_available:
        click.echo(f"Configuration {name} already exists.")
        sys.exit(0)

    # create config in ctx location
    configuration_wizard(ctx)
    click.echo("New configuration created.")

#
#   files
#
@cli_node.command(name="files")
@click.argument("name", default=None, required=False)
def cli_node_files(name):
    """Print out the paths of important files.
    
    If the specified configuration cannot be found, it exits. Otherwise
    it returns the absolute path to the output. 
    """
    # select configuration name if none supplied
    name = name if name else select_configuration_questionaire('node') 

    # create new configuration
    ctx = util.NodeContext(APPNAME, name)

    # check if config file exists, if not create it in the ctx location
    if not ctx.config_available:
        click.echo(f"Configuration cannot be found. Exiting {APPNAME}.")
        sys.exit(0)
    
    ctx.init(ctx.config_file)
    
    # return path of the configuration
    click.echo(f"Configuration file = {ctx.config_file}")
    click.echo(f"Log file           = {ctx.log_file}")
    click.echo(f"Database labels and files")
    for label, path in ctx.database_files.items():
        click.echo(f" - {label:15} = {path}")

#
#   start
#
@cli_node.command(name='start')
@click.argument("name", default=None, required=False)
@click.option('-c', '--config', 
    default=None, 
    help='absolute path to configuration-file; overrides NAME'
)
def cli_node_start(name, config):
    """Start the node instance.
    
    If no name or config is specified the default.yaml configuation is used. 
    In case the configuration file not excists, a questionaire is
    invoked to create one. Note that in this case it is not possible to
    specify specific environments for the configuration (e.g. test, 
    prod, acc). 
    """

    # select configuration name if none supplied
    name = name if name else select_configuration_questionaire('node') 

    # create dummy node context
    ctx = util.NodeContext(APPNAME, name)
    
    # check if config file excists
    cfg_file = config if config else ctx.config_file
    if not os.path.exists(cfg_file):
        
        # user decides not to create config file
        click.echo(f"Configation file {cfg_file} does not exist.")
        if click.confirm("Do you want to create this config now?"):
            # start commandline questionaire to gen. config file
            configuration_wizard(ctx, cfg_file)
        else:
            click.echo(f"Exiting {APPNAME}.")
            sys.exit(0)
        
        
    # load configuration and initialize logging system
    ctx.init(cfg_file)

    # run the node application
    node.run(ctx)
