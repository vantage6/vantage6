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
* node attach
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

from vantage6.common.globals import (
    STRING_ENCODING,
    APPNAME
)
from vantage6.cli.globals import (
    DEFAULT_NODE_ENVIRONMENT,
    DEFAULT_NODE_SYSTEM_FOLDERS
)
from vantage6.cli.context import NodeContext
from vantage6.cli.configuration_wizard import (
    configuration_wizard,
    select_configuration_questionaire
)

import vantage6.common.colorer
from colorama import init, Fore, Back, Style

init()

def echo(msg, level = "info"):
    type_ = {
        "error": f"[{Fore.RED}error{Style.RESET_ALL}]",
        "warn": f"[{Fore.YELLOW}warn{Style.RESET_ALL}]",
        "info": f"[{Fore.GREEN}info{Style.RESET_ALL}]"
    }.get(level)
    click.echo(f"{type_} - {msg}")

def info(msg):
    echo(msg, "info")

def warning(msg):
    echo(msg, "warn")

def error(msg):
    echo(msg, "error")


@click.group(name="node")
def cli_node():
    """Subcommand `vnode`."""
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
        filters={"label":f"{APPNAME}-type=node"})
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
    configs, f1 = NodeContext.available_configurations(
        system_folders=True)
    for config in configs:
        status = running if f"{APPNAME}-{config.name}-system" in \
            running_node_names else stopped
        click.echo(
            f"{config.name:25}"
            f"{str(config.available_environments):32}"
            f"{status:25} System "
        )

    # user folders
    configs, f2 = NodeContext.available_configurations(
        system_folders=False)
    for config in configs:
        status = running if f"{APPNAME}-{config.name}-user" in \
            running_node_names else stopped
        click.echo(
            f"{config.name:25}"
            f"{str(config.available_environments):32}"
            f"{status:25} User   "
        )

    click.echo("-"*85)
    if len(f1)+len(f2):
        warning(
             f"{Fore.RED}Failed imports: {len(f1)+len(f2)}{Style.RESET_ALL}")

#
#   new
#
@cli_node.command(name="new")
@click.option("-n", "--name", default=None)
@click.option('-e', '--environment',
    default="",
    help='configuration environment to use'
)
@click.option('--system', 'system_folders',
    flag_value=True
)
@click.option('--user', 'system_folders',
    flag_value=False,
    default=DEFAULT_NODE_SYSTEM_FOLDERS
)
def cli_node_new_configuration(name, environment, system_folders):
    """Create a new configation file.

    Checks if the configuration already exists. If this is not the case
    a questionaire is invoked to create a new configuration file.
    """
    # select configuration name if none supplied
    if not name:
        name = q.text("Please enter a configuration-name:").ask()

    if not environment:
        environment = q.select(
            "Please select the environment you want to configure:",
            ["application", "prod", "acc", "test", "dev"]
        ).ask()

    # check that this config does not exist
    if NodeContext.config_exists(name,environment,system_folders):
        error(
            f"Configuration {name} and environment"
            f"{environment} already exists!"
        )

    # create config in ctx location
    cfg_file = configuration_wizard(name, environment,system_folders)
    info(f"New configuration created: {Fore.GREEN}{cfg_file}{Style.RESET_ALL}")

#
#   files
#
@cli_node.command(name="files")
@click.option("-n", "--name",
    default=None,
    help="configuration name"
)
@click.option('-e', '--environment',
    default=DEFAULT_NODE_ENVIRONMENT,
    help='configuration environment to use'
)
@click.option('--system', 'system_folders',
    flag_value=True
)
@click.option('--user', 'system_folders',
    flag_value=False,
    default=DEFAULT_NODE_SYSTEM_FOLDERS
)
def cli_node_files(name, environment, system_folders):
    """Print out the paths of important files.

    If the specified configuration cannot be found, it exits. Otherwise
    it returns the absolute path to the output.
    """
    # select configuration name if none supplied
    name, environment = (name, environment) if name else \
        select_configuration_questionaire(system_folders)

    # raise error if config could not be found
    if not NodeContext.config_exists(name,environment,system_folders):
        error(
            f"The configuration {Fore.RED}{name}{Style.RESET_ALL} with "
            f"environment {Fore.RED}{environment}{Style.RESET_ALL} could "
            f"not be found."
        )
        # raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), name)

    # create node context
    ctx = NodeContext(name,environment=environment,
        system_folders=system_folders)

    # return path of the configuration
    info(f"Configuration file = {ctx.config_file}")
    info(f"Log file           = {ctx.log_file}")
    info(f"data folders       = {ctx.data_dir}")
    info(f"Database labels and files")
    for label, path in ctx.databases.items():
        print("The correct label and path is as follows:")
        info(f" - {label:15} = {path}")

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
    default=DEFAULT_NODE_ENVIRONMENT,
    help='configuration environment to use'
)
@click.option('--system', 'system_folders',
    flag_value=True
)
@click.option('--user', 'system_folders',
    flag_value=False,
    default=DEFAULT_NODE_SYSTEM_FOLDERS
)
@click.option('-d', '--develop',
    default=False,
    help="Source code for developer container"
)
@click.option('-t', '--tag',
    default="default",
    help="Node Docker container tag to use"
)
def cli_node_start(name, config, environment, system_folders, develop, tag):
    """ Start the node instance.

        If no name or config is specified the default.yaml configuation is used.
        In case the configuration file not excists, a questionaire is
        invoked to create one. Note that in this case it is not possible to
        specify specific environments for the configuration (e.g. test,
        prod, acc).
    """
    info("Starting node...")

    info("Finding Docker deamon")
    docker_client = docker.from_env()
    check_if_docker_deamon_is_running(docker_client)

    # in case a configuration file is given, we by pass all the helper
    # stuff since you know what you are doing
    if config:
        ctx = NodeContext.from_external_config_file(config, environment,
            system_folders)
    else:
        # in case no name is supplied, ask user to select one
        name, environment = (name, environment) if name else \
            select_configuration_questionaire(system_folders)

        # check that config exists in the APP, if not a questionaire will
        # be invoked
        if not NodeContext.config_exists(name, environment, system_folders):
            if q.confirm(f"Configuration {name} using environment "
                f"{environment} does not exists. Do you want to create "
                f"this config now?").ask():
                configuration_wizard("node", name, environment=environment,
                    system_folders=system_folders)
            else:
                error("Config file couldn't be loaded")
                sys.exit(0)

        NodeContext.LOGGING_ENABLED = False
        ctx = NodeContext(name, environment, system_folders)

    # check that this node is not already running
    running_nodes = docker_client.containers.list(
        filters={"label":f"{APPNAME}-type=node"})
    for node in running_nodes:
        post_ = "system" if system_folders else "user"
        if node.name == f"{APPNAME}-{name}-{post_}":
            error(f"Node {Fore.RED}{name}{Style.RESET_ALL} is already running")
            exit()


    # make sure the (host)-task and -log dir exists
    info("Checking that data and log dirs exist")

    ctx.data_dir.mkdir(parents=True, exist_ok=True)
    ctx.log_dir.mkdir(parents=True, exist_ok=True)

    # specify mount-points
    info("Mounting files & folders")
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
            warning(f"private key file provided {rsa_file}, but does not exists")

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
        port = {"80/tcp": ("127.0.0.1", 8081)}
        info(f"proxy-server attached {port}")
    else:
        port = None
        # 1) --tag, 2) config 3) latest
        tag_ = tag if tag != "default" else ctx.config.get("tag", "latest")
        container_image = f"harbor.distributedlearning.ai/infrastructure/node:{tag_}"
        info(f"Default container is used <{container_image}>")

    # pull the latest image
    info("Pulling latest node Docker image")
    docker_client.images.pull(container_image)

    # create data volume which can be used by this node instance
    info("Create Docker data volume")
    data_volume = docker_client.volumes.create(
        f"{ctx.docker_container_name}-vol"
    )

    info("Run Docker container")
    container = docker_client.containers.run(
        container_image,
        command=[ctx.config_file_name, ctx.environment],
        mounts=mounts,
        volumes={data_volume.name: {'bind': '/mnt/data-volume', 'mode': 'rw'}},
        detach=True, # not attach,
        labels={
            f"{APPNAME}-type": "node",
            "system": str(system_folders),
            "name": ctx.config_file_name
        },
        environment={
            "DATA_VOLUME_NAME": data_volume.name,
        },
        ports=port,
        name=ctx.docker_container_name,
        auto_remove=True # not attach
    )

    info(f"Succes! container id = {container}")


#
#   stop
#
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
    default=DEFAULT_NODE_SYSTEM_FOLDERS
)
@click.option('--all', 'all_nodes',
    flag_value=True
)
def cli_node_stop(name, system_folders, all_nodes):
    """Stop a running container. """

    client = docker.from_env()
    check_if_docker_deamon_is_running(client)

    running_nodes = client.containers.list(
        filters={"label":f"{APPNAME}-type=node"})

    if not running_nodes:
        warning("No nodes are currently running.")
        return

    running_node_names = [node.name for node in running_nodes]

    if all_nodes:
        for name in running_node_names:
            container = client.containers.get(name)
            container.kill()
            info(f"Stopped the {Fore.GREEN}{name}{Style.RESET_ALL} Node.")
    else:
        if not name:
            name = q.select("Select the node you wish to stop:",
                choices=running_node_names).ask()
        else:

            post_fix = "system" if system_folders else "user"
            name = f"{APPNAME}-{name}-{post_fix}"

        if name in running_node_names:
            container = client.containers.get(name)
            container.kill()
            info(f"Stopped the {Fore.GREEN}{name}{Style.RESET_ALL} Node.")
        else:
            error(f"{Fore.RED}{name}{Style.RESET_ALL} is not running?")


#
#   attach
#
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
    default=DEFAULT_NODE_SYSTEM_FOLDERS
)
def cli_node_attach(name, system_folders):
    """Attach the logs from the docker container to the terminal."""

    client = docker.from_env()
    check_if_docker_deamon_is_running(client)

    running_nodes = client.containers.list(
        filters={"label":f"{APPNAME}-type=node"})
    running_node_names = [node.name for node in running_nodes]

    if not name:
        name = q.select("Select the node you wish to inspect:",
            choices=running_node_names).ask()
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}"

    if name in running_node_names:
        container = client.containers.get(name)
        logs = container.attach(stream=True, logs=True)
        Thread(target=print_log_worker, args=(logs,), daemon=True).start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                info("Closing log file. Keyboard Interrupt.")
                exit(0)
    else:
        error(f"{Fore.RED}{name}{Style.RESET_ALL} was not running!?")

def print_log_worker(logs_stream):
    for log in logs_stream:
        print(log.decode(STRING_ENCODING))

def check_if_docker_deamon_is_running(docker_client):
    try:
        docker_client.ping()
    except Exception as e:
        error("Docker socket can not be found. Make sure Docker is running.")
        exit()
