"""Node Manager Command Line Interface

The node manager is responsible for: 
1) Creating, updating and deleting configurations (=nodes).
2) Starting, Stopping nodes 

Configuration Commands
* node new 
* node list
* node files 
* node start
* node stop
* node inspect
"""
import click
import yaml
import os
import sys
import appdirs
import questionary as q
import errno
import docker
import time

from docker.errors import DockerException
from pathlib import Path
from threading import Thread

import vantage.constants as constants

from vantage import util, node

from vantage.util.context import (
    configuration_wizard, select_configuration_questionaire)
from vantage.constants import STRING_ENCODING

from colorama import init, Fore, Back, Style
init()


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
    
    client = docker.from_env()
    check_if_docker_deamon_is_running(client)

    running_nodes = client.containers.list(
        filters={"label":f"{constants.APPNAME}-type=node"})
    running_node_names = []
    for node in running_nodes:
        running_node_names.append(node.name)

    header = \
        "\nName"+(21*" ") + \
        "Environments"+(20*" ") + \
        "Status"+(10*" ") + \
        "System/User"
    
    click.echo(header)
    click.echo("-"*len(header))
    
    running = Fore.GREEN + "Online" + Style.RESET_ALL
    stopped = Fore.RED + "Offline" + Style.RESET_ALL

    # system folders
    configs, f1 = util.NodeContext.available_configurations(
        system_folders=True)
    for config in configs:
        status = running if f"{constants.APPNAME}-{config.name}-system" in \
            running_node_names else stopped
        click.echo(
            f"{config.name:25}"
            f"{str(config.available_environments):32}"
            f"{status:25} System "
        ) 

    # user folders
    configs, f2 = util.NodeContext.available_configurations(
        system_folders=False)
    for config in configs:
        status = running if f"{constants.APPNAME}-{config.name}-user" in \
            running_node_names else stopped
        click.echo(
            f"{config.name:25}"
            f"{str(config.available_environments):32}"
            f"{status:25} User   "
        ) 

    click.echo("-"*85)
    if len(f1)+len(f2):
        click.echo(
            Fore.RED + f"Failed imports: {len(f1)+len(f2)}" + Style.RESET_ALL)

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
    if util.NodeContext.config_exists(name,environment,system_folders):
        raise FileExistsError(f"Configuration {name} and environment" 
            f"{environment} already exists!")

    # create config in ctx location
    cfg_file = configuration_wizard("node", name, environment, 
        system_folders)
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
    if not util.NodeContext.config_exists(name,environment,system_folders):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), name)
    
    # create node context
    ctx = util.NodeContext(name,environment=environment, 
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
@click.option('-d', '--develop', 
    default=False,
    help="Source code for developer container"
)
def cli_node_start(name, config, environment, system_folders, develop):
    """ Start the node instance.
    
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
        
        # in case no name is supplied, ask user to select one
        name, environment = (name, environment) if name else \
            select_configuration_questionaire('node', system_folders) 
                
        # check that config exists in the APP, if not a questionaire will
        # be invoked
        if not util.NodeContext.config_exists(name,environment,system_folders):
            if q.confirm(f"Configuration {name} using environment "
                f"{environment} does not exists. Do you want to create "
                f"this config now?").ask():
                configuration_wizard("node", name, environment=environment, 
                    system_folders=system_folders)
            else:
                sys.exit(0)

        util.NodeContext.LOGGING_ENABLED = False
        ctx = util.NodeContext(name, environment, system_folders)
    
    # make sure the (host)-task and -log dir exists
    ctx.data_dir.mkdir(parents=True, exist_ok=True)
    ctx.log_dir.mkdir(parents=True, exist_ok=True)

    docker_client = docker.from_env()
    check_if_docker_deamon_is_running(docker_client)
    
    # specify mount-points 
    mounts = [
        # TODO multiple database support
        docker.types.Mount("/mnt/database.csv", str(ctx.databases["default"]),
            type="bind"),
        docker.types.Mount("/mnt/log", str(ctx.log_dir), type="bind"),
        docker.types.Mount("/mnt/data", str(ctx.data_dir), type="bind"),
        docker.types.Mount("/mnt/config", str(ctx.config_dir), type="bind"),
        docker.types.Mount("/var/run/docker.sock", "//var/run/docker.sock", 
            type="bind"),
    ]
    
    rsa_file = ctx.config.get("encryption", {}).get("private_key")
    if rsa_file:
        if Path(rsa_file).exists():
            mounts.append(
                docker.types.Mount("/mnt/private_key.pem", rsa_file, 
                    type="bind")
            )
        else: 
            print(f"private key file provided {rsa_file}, but does not exists")

    # in case a development environment is run, we need to do a few extra things
    # and run a devcon container (see develop.Dockerfile)
    # TODO these filepaths need to be set int the config file
    if develop:
        mounts.append(
            docker.types.Mount("/src", 
            develop, type="bind")
        )
        container_image = "harbor.distributedlearning.ai/infrastructure/dev"
        # attach proxy server for debugging to the host machine
        port = {"80/tcp":("127.0.0.1",8081)}
        print(f"proxy-server attached {port}")
    else:
        port = None
        container_image = "harbor.distributedlearning.ai/infrastructure/node"

    # create data volume which can be used by this node instance
    data_volume = docker_client.volumes.create(
        f"{ctx.docker_container_name}-vol"
    )
    
    container = docker_client.containers.run(
        container_image,
        command=[ctx.config_file_name, ctx.environment],
        mounts=mounts,
        volumes={data_volume.name: {'bind': '/mnt/data-volume', 'mode': 'rw'}},
        detach=True,#not attach,
        labels={
            f"{constants.APPNAME}-type": "node", 
            "system": str(system_folders), 
            "name": ctx.config_file_name
        },
        environment={
            "DATA_VOLUME_NAME": data_volume.name,
        },
        ports=port,
        name=ctx.docker_container_name,
        auto_remove=True#not attach
    )

    click.echo(f"Running, container id = {container}")

@cli_node.command(name='stop')
@click.option("-n","--name", 
    default=None,
    help="configuration name"
)
@click.option('--system', 'system_folders', 
    flag_value=True
)
@click.option('--user', 'system_folders', 
    flag_value=False, 
    default=constants.DEFAULT_NODE_SYSTEM_FOLDERS
)
def cli_node_stop(name, system_folders):
    """Stop a running container. """

    client = docker.from_env()
    check_if_docker_deamon_is_running(client)

    running_nodes = client.containers.list(
        filters={"label":f"{constants.APPNAME}-type=node"})
    
    if not running_nodes:
        click.echo("No nodes are currently running.")
        return 

    running_node_names = [node.name for node in running_nodes]
    if not name:
        name = q.select("Select the node you wish to stop:",
            choices=running_node_names).ask()
    else: 
        post_fix = "system" if system_folders else "user"
        name = f"{constants.APPNAME}-{name}-{post_fix}" 
    
    if name in running_node_names:
        container = client.containers.get(name)
        container.kill()
        click.echo(f"Node {name} stopped.")
    else: 
        click.echo(Fore.RED + f"{name} was not running!?")

@cli_node.command(name='attach')
@click.option("-n","--name", 
    default=None,
    help="configuration name"
)
@click.option('--system', 'system_folders', 
    flag_value=True
)
@click.option('--user', 'system_folders', 
    flag_value=False, 
    default=constants.DEFAULT_NODE_SYSTEM_FOLDERS
)
def cli_node_attach(name, system_folders):
    """Attach the logs from the docker container to the terminal."""

    client = docker.from_env()
    check_if_docker_deamon_is_running(client)

    running_nodes = client.containers.list(
        filters={"label":f"{constants.APPNAME}-type=node"})
    running_node_names = [node.name for node in running_nodes]
    
    if not name:
        name = q.select("Select the node you wish to inspect:",
            choices=running_node_names).ask()
    else: 
        post_fix = "system" if system_folders else "user"
        name = f"{constants.APPNAME}-{name}-{post_fix}" 

    if name in running_node_names:
        container = client.containers.get(name)
        logs = container.attach(stream=True, logs=True)
        Thread(target=print_log_worker, args=(logs,), daemon=True).start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                exit(0)
    else:
        click.echo(Fore.RED + f"{name} was not running!?")

def print_log_worker(logs_stream):
    for log in logs_stream:
        print(log.decode(STRING_ENCODING))

def check_if_docker_deamon_is_running(docker_client):
    try:
        docker_client.ping()
    except Exception as e:
        click.echo(
            "Docker socket not found. Is Docker running? Exiting")
        exit()
