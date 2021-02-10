import click
import os
import sys
import questionary as q
import errno

import vantage6.node.globals as constants

from colorama import Fore, Style
from pathlib import Path

from vantage6 import node
from vantage6.node.context import NodeContext, DockerNodeContext
from vantage6.common import warning, info, error, check_config_write_permissions

from vantage6.cli.configuration_wizard import (
    configuration_wizard,
    select_configuration_questionaire
)
from vantage6.node._version import __version__


@click.group(name="vnode-local")
def cli_node():
    """Command `vnode-local`."""
    pass


#
#   list
#
@cli_node.command(name="list")
def cli_node_list():
    """Lists all nodes in the default configuration directories."""

    # FIXME: use package 'table' for this.
    click.echo("\nName"+(21*" ")+"Environments"+(21*" ")+"System/User")
    click.echo("-" * 70)

    configs, f1 = NodeContext.available_configurations(system_folders=True)
    for config in configs:
        click.echo(f"{config.name:25}{str(config.available_environments):32} "
                   f"System ")

    configs, f2 = NodeContext.available_configurations(system_folders=False)
    for config in configs:
        click.echo(f"{config.name:25}{str(config.available_environments):32} "
                   f"User   ")

    click.echo("-"*70)
    warning(f"Number of failed imports: "
            f"{Fore.YELLOW}{len(f1)+len(f2)}{Style.RESET_ALL}")
#
#   new
#
@cli_node.command(name="new")
@click.option("-n", "--name", default=None)
@click.option('-e', '--environment',
              default=None,
              help='configuration environment to use')
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=constants.DEFAULT_NODE_SYSTEM_FOLDERS)
def cli_node_new_configuration(name, environment, system_folders):
    """Create a new configation file.

    Checks if the configuration already exists. If this is not the case
    a questionaire is invoked to create a new configuration file.
    """
    # select configuration name if none supplied
    if not name:
        name = q.text("Please enter a configuration-name:").ask()
        name_new = name.replace(" ", "-")
        if name != name_new:
            info(f"Replaced spaces from configuration name: {name}")
            name = name_new

    if not environment:
        environment = q.select(
            "Please select the environment you want to configure:",
            ["application", "prod", "acc", "test", "dev"]
        ).ask()

    # Check that we can write in this folder
    if not check_config_write_permissions(system_folders):
        error("Your user does not have write access to all folders. Exiting")
        exit(1)

    # check that this config does not exist
    if NodeContext.config_exists(name, environment, system_folders):
        raise FileExistsError(f"Configuration {name} and environment"
                              f"{environment} already exists!")

    # create config in ctx location
    cfg_file = configuration_wizard("node", name, environment, system_folders)
    info(f"New configuration created: {Fore.GREEN}{cfg_file}{Style.RESET_ALL}")

#
#   files
#
@cli_node.command(name="files")
@click.option("-n", "--name", default=None, help="configuration name")
@click.option('-e', '--environment',
              default=constants.DEFAULT_NODE_ENVIRONMENT,
              help='configuration environment to use')
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=constants.DEFAULT_NODE_SYSTEM_FOLDERS)
def cli_node_files(name, environment, system_folders):
    """Print out the paths of important files.

    If the specified configuration cannot be found, it exits. Otherwise
    it returns the absolute path to the output.
    """
    # select configuration name if none supplied
    name, environment = (name, environment) if name else \
        select_configuration_questionaire("node", system_folders)

    # raise error if config could not be found
    if not NodeContext.config_exists(name, environment, system_folders):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), name)

    # create node context
    ctx = NodeContext(name, environment=environment,
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
@click.option("-n", "--name", default=None, help="configuration name")
@click.option("-c", "--config", default=None,
              help='absolute path to configuration-file; overrides NAME')
@click.option('-e', '--environment',
              default=constants.DEFAULT_NODE_ENVIRONMENT,
              help='configuration environment to use')
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=constants.DEFAULT_NODE_SYSTEM_FOLDERS)
@click.option('--dockerized/-non-dockerized', default=False)
def cli_node_start(name, config, environment, system_folders, dockerized):
    """Start the node instance.

    If no name or config is specified the default.yaml configuation is used.
    In case the configuration file not excists, a questionaire is
    invoked to create one. Note that in this case it is not possible to
    specify specific environments for the configuration (e.g. test,
    prod, acc).
    """
    ContextClass = DockerNodeContext if dockerized else NodeContext

    # in case a configuration file is given, we bypass all the helper
    # stuff since you know what you are doing
    if config:
        name = Path(config).stem
        ctx = ContextClass(name, environment, system_folders, config)

    else:
        # in case no name is supplied, ask user to select one
        if not name:
            name, environment = select_configuration_questionaire(
                "node",
                system_folders
            )

        # check that config exists in the APP, if not a questionaire will
        # be invoked
        if not ContextClass.config_exists(name, environment, system_folders):
            question = f"Configuration '{name}' using environment"
            question += f" '{environment}' does not exist.\n  Do you want to"
            question += f" create this config now?"

            if q.confirm(question).ask():
                configuration_wizard("node", name, environment, system_folders)

            else:
                sys.exit(0)

        # create dummy node context
        ctx = ContextClass(name, environment, system_folders)

    # run the node application
    node.run(ctx)


#
#   version
#
@cli_node.command(name='version')
def cli_node_version():
    """Returns current version of vantage6 services installed."""
    click.echo(__version__)