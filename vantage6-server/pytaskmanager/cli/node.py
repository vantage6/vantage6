import click
import yaml
import os
import sys
import appdirs
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
import datetime
@cli_node.command(name="list")
def cli_node_list():
    """Lists all nodes in the default configuration directory."""
    
    # get user/system application directories
    d = appdirs.AppDirs(APPNAME,"")
    system_folder = Path(d.site_config_dir) / "node"
    user_folder = Path(d.user_config_dir) / "node"

    # check for files in the user-directories
    user_files = user_folder.glob("*.yaml")
    system_files = system_folder.glob("*.yaml")

    click.echo("\nName"+(12*" ")+"Environments"+(14*" ")+"Application"+(5*" ")+"System/User"+(5*" ")+"Time")
    click.echo("-"*100)

    for env in ["user", "system"]:
        files = eval(env+"_files")
        for file_ in files:
            config = yaml.safe_load(open(file_))
            envs = "".join(config.get('environments', {}).keys()) or "-"
            app = ("yes" if config.get('application', False) else "no") 
            time = datetime.datetime.fromtimestamp(file_.stat().st_mtime)
            folder = env 
            click.echo(f"{file_.stem:16}{str(envs):25} {app:15} {folder:15} {time}")

#
#   new
#
@cli_node.command(name="new")
@click.argument("name", default=None, required=False)
@click.option('-e', '--environment', 
    default=None, 
    help='configuration environment to use'
)
def cli_node_new_configuration(name, environment):
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
    cfg_file = configuration_wizard(ctx, environment=environment)
    click.echo(f"New configuration created: {cfg_file}")

#
#   files
#
@cli_node.command(name="files")
@click.argument("name", default=None, required=False)
@click.option('-e', '--environment', 
    default=None, 
    help='configuration environment to use'
)
def cli_node_files(name, environment):
    """Print out the paths of important files.
    
    If the specified configuration cannot be found, it exits. Otherwise
    it returns the absolute path to the output. 
    """
    # select configuration name if none supplied
    name = name if name else select_configuration_questionaire('node') 

    # create default node context
    ctx = util.NodeContext(APPNAME, name)

    # check if config file exists, if not create it in the ctx location
    if not ctx.config_available:
        click.echo(f"Configuration cannot be found. Exiting {APPNAME}.")
        sys.exit(0)
    
    # inject context with the user specified configuration
    ctx.init(ctx.config_file, environment)
    
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
@click.option('-e', '--environment', 
    default="application", 
    help='configuration environment to use'
)
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False, default=False)
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
        ctx = util.NodeContext.from_external_config_file(config, environment, 
            system_folders)
    else:
        
        # in case no nanem is supplied, ask user to select one
        name = name if name else select_configuration_questionaire('node') 
                
        # check that config exists in the APP, if not a questionaire will
        # be invoked
        if not util.NodeContext.config_exists(name,environment,system_folders):
            if q.confirm(f"Configuration {name} does not exists. "
                "Do you want to create this config now?").ask():
                configuration_wizard("node", name, environment=environment, 
                    system_folders=system_folders)
            else:
                click.echo(f"Exiting {APPNAME}.")
                sys.exit(0)
        
        # create dummy node context
        ctx = util.NodeContext(name, environment, system_folders)
        
    # run the node application
    node.run(ctx)
