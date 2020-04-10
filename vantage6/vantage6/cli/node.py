""" Node Manager Command Line Interface

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
import sys
import questionary as q
import docker
import time
import os.path

from pathlib import Path
from threading import Thread
from colorama import Fore, Style

from vantage6.common.globals import (STRING_ENCODING, APPNAME)
from vantage6.cli.globals import (
    DEFAULT_NODE_ENVIRONMENT as N_ENV,
    DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
)
from vantage6.cli.context import NodeContext
from vantage6.cli.configuration_wizard import (
    configuration_wizard,
    select_configuration_questionaire
)
from vantage6.common import (warning, error, info, debug)


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
        filters={"label": f"{APPNAME}-type=node"})
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
@click.option('-e', '--environment', default="",
              help='configuration environment to use')
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL)
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
    if NodeContext.config_exists(name, environment, system_folders):
        error(
            f"Configuration {name} and environment"
            f"{environment} already exists!"
        )

    # create config in ctx location
    cfg_file = configuration_wizard(name, environment, system_folders)
    info(f"New configuration created: {Fore.GREEN}{cfg_file}{Style.RESET_ALL}")

#
#   files
#
@cli_node.command(name="files")
@click.option("-n", "--name", default=None, help="configuration name")
@click.option('-e', '--environment', default=N_ENV,
              help='configuration environment to use')
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL)
def cli_node_files(name, environment, system_folders):
    """ Prints location important files.

        If the specified configuration cannot be found, it exits. Otherwise
        it returns the absolute path to the output.
    """
    # select configuration name if none supplied
    name, environment = (name, environment) if name else \
        select_configuration_questionaire(system_folders)

    # raise error if config could not be found
    if not NodeContext.config_exists(name, environment, system_folders):
        error(
            f"The configuration {Fore.RED}{name}{Style.RESET_ALL} with "
            f"environment {Fore.RED}{environment}{Style.RESET_ALL} could "
            f"not be found."
        )

    # create node context
    ctx = NodeContext(name, environment=environment,
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
help_ = {
    'config': 'absolute path to configuration-file; overrides NAME',
    'environment': 'configuration environment to use',
}
@cli_node.command(name='start')
@click.option("-n", "--name", default=None, help="configuration name")
@click.option("-c", "--config", default=None, help=help_['config'])
@click.option('-e', '--environment', default=N_ENV, help=help_['environment'])
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL)
@click.option('-i', '--image', default=None, help="Node Docker image to use")
@click.option('--keep/--auto-remove', default=False,
              help="Keep image after finishing")
@click.option('--mount-src', default='',
              help="mount vantage6-node package source")
def cli_node_start(name, config, environment, system_folders, image, keep,
                   mount_src):
    """Start the node instance.

        If no name or config is specified the default.yaml configuation is
        used. In case the configuration file not excists, a questionaire is
        invoked to create one. Note that in this case it is not possible to
        specify specific environments for the configuration (e.g. test,
        prod, acc).
    """
    info("Starting node...")
    info("Finding Docker deamon")
    docker_client = docker.from_env()
    check_if_docker_deamon_is_running(docker_client)

    if config:
        ctx = NodeContext(name, environment, system_folders, config)

    else:
        # in case no name is supplied, ask the user to select one
        if not name:
            name, environment = select_configuration_questionaire(
                system_folders)

        # check that config exists, if not a questionaire will be invoked
        if not NodeContext.config_exists(name, environment, system_folders):
            question = f"Configuration '{name}' using environment"
            question += f" '{environment}' does not exist.\n  Do you want to"
            question += f" create this config now?"

            if q.confirm(question).ask():
                configuration_wizard(name, environment, system_folders)

            else:
                error("Config file couldn't be loaded")
                sys.exit(0)

        NodeContext.LOGGING_ENABLED = False
        ctx = NodeContext(name, environment, system_folders)

    # check that this node is not already running
    running_nodes = docker_client.containers.list(
        filters={"label": f"{APPNAME}-type=node"}
    )

    suffix = "system" if system_folders else "user"
    for node in running_nodes:
        if node.name == f"{APPNAME}-{name}-{suffix}":
            error(f"Node {Fore.RED}{name}{Style.RESET_ALL} is already running")
            exit()

    # make sure the (host)-task and -log dir exists
    info("Checking that data and log dirs exist")
    ctx.data_dir.mkdir(parents=True, exist_ok=True)
    ctx.log_dir.mkdir(parents=True, exist_ok=True)

    if image is None:
        image = ctx.config.get(
            "image",
            "harbor.distributedlearning.ai/infrastructure/node:latest"
        )

    info(f"Pulling latest node image '{image}'")
    try:
        docker_client.images.pull(image)
    except Exception:
        warning(' ... alas, no dice!')
    else:
        info(" ... succes!")

    info("Creating Docker data volume")
    data_volume = docker_client.volumes.create(
        f"{ctx.docker_container_name}-vol")

    info("Creating file & folder mounts")
    # FIXME: should only mount /mnt/database.csv if it is a file!
    # FIXME: should obtain mount points from DockerNodeContext
    mounts = [
        # (target, source)
        ("/mnt/database.csv", str(ctx.databases["default"])),
        ("/mnt/log", str(ctx.log_dir)),
        ("/mnt/data", data_volume.name),
        ("/mnt/config", str(ctx.config_dir)),
        ("/var/run/docker.sock", "/var/run/docker.sock"),
    ]

    if mount_src:
        # If mount_src is a relative path, docker willl consider it a volume.
        mount_src = os.path.abspath(mount_src)
        mounts.append(('/vantage6/vantage6-node', mount_src))

    # FIXME: Code duplication: Node.__init__() (vantage6/node/__init__.py)
    #   uses a lot of the same logic. Suggest moving this to
    #   ctx.get_private_key()
    filename = ctx.config.get("encryption", {}).get("private_key")

    # filename may be set to an empty string
    if not filename:
        filename = 'private_key.pem'

    # Location may be overridden by the environment
    filename = os.environ.get('PRIVATE_KEY', filename)

    # If ctx.get_data_file() receives an absolute path, it is returned as-is
    fullpath = Path(ctx.get_data_file(filename))

    if fullpath:
        if Path(fullpath).exists():
            mounts.append(("/mnt/private_key.pem", str(fullpath)))
        else:
            warning(f"private key file provided {fullpath}, "
                    "but does not exists")

    volumes = {}
    for mount in mounts:
        volumes[mount[1]] = {'bind': mount[0], 'mode': 'rw'}

    # Be careful not to use 'environment' as it would override the function
    # argument ;-).
    env = {
        "DATA_VOLUME_NAME": data_volume.name,
        "DATABASE_URI": "/mnt/database.csv",
        "PRIVATE_KEY": "/mnt/private_key.pem"
    }

    cmd = f'vnode-local start -c /mnt/config/{name}.yaml -n {name} -e '\
          f'{environment} --dockerized'

    info(f"Runing Docker container")
    # debug(f"  with command: '{cmd}'")
    # debug(f"  with mounts: {volumes}")
    # debug(f"  with environment: {env}")
    container = docker_client.containers.run(
        image,
        command=cmd,
        volumes=volumes,
        detach=True,
        labels={
            f"{APPNAME}-type": "node",
            "system": str(system_folders),
            "name": ctx.config_file_name
        },
        environment=env,
        name=ctx.docker_container_name,
        auto_remove=not keep,
        tty=True
    )

    info(f"Succes! container id = {container}")


#
#   stop
#
@cli_node.command(name='stop')
@click.option("-n", "--name", default=None, help="configuration name")
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL)
@click.option('--all', 'all_nodes', flag_value=True)
def cli_node_stop(name, system_folders, all_nodes):
    """Stop a running container. """

    client = docker.from_env()
    check_if_docker_deamon_is_running(client)

    running_nodes = client.containers.list(
        filters={"label": f"{APPNAME}-type=node"})

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
@click.option("-n", "--name", default=None, help="configuration name")
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL)
def cli_node_attach(name, system_folders):
    """Attach the logs from the docker container to the terminal."""

    client = docker.from_env()
    check_if_docker_deamon_is_running(client)

    running_nodes = client.containers.list(
        filters={"label": f"{APPNAME}-type=node"})
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
        print(log.decode(STRING_ENCODING), end="")


def check_if_docker_deamon_is_running(docker_client):
    try:
        docker_client.ping()
    except Exception:
        error("Docker socket can not be found. Make sure Docker is running.")
        exit(1)
