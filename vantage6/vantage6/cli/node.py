"""
The node module contains the CLI commands for the node manager. The following
commands are available:

    * vnode new
    * vnode list
    * vnode files
    * vnode start
    * vnode stop
    * vnode attach
    * vnode clean
    * vnode remove
    * vnode version
    * vnode create-private-key
"""
import click
import sys
import questionary as q
import docker
import time
import os.path
import itertools

from typing import Iterable
from pathlib import Path
from threading import Thread
from colorama import Fore, Style
from shutil import rmtree

from vantage6.common import (
    warning, error, info, debug,
    bytes_to_base64s, check_config_writeable,
    get_database_config
)
from vantage6.common.globals import (
    STRING_ENCODING,
    APPNAME,
    DEFAULT_DOCKER_REGISTRY,
    DEFAULT_NODE_IMAGE,
    DEFAULT_NODE_IMAGE_WO_TAG,
)
from vantage6.common.globals import VPN_CONFIG_FILE
from vantage6.common.docker.addons import (
  pull_if_newer,
  remove_container_if_exists,
  check_docker_running
)
from vantage6.common.encryption import RSACryptor
from vantage6.client import UserClient

from vantage6.cli.context import NodeContext
from vantage6.cli.globals import (
    DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
)
from vantage6.cli.configuration_wizard import (
    configuration_wizard,
    select_configuration_questionaire,
    NodeConfigurationManager
)
from vantage6.cli.utils import (
    check_config_name_allowed, check_if_docker_daemon_is_running,
    prompt_config_name, remove_file
)
from vantage6.cli import __version__


@click.group(name="node")
def cli_node() -> None:
    """
    The `vnode` commands allow you to manage your vantage6 node instances.
    """
    pass


#
#   list
#
@cli_node.command(name="list")
def cli_node_list() -> None:
    """
    Lists all node configurations.

    Note that this command cannot find node configuration files in custom
    directories.
    """

    check_docker_running()
    client = docker.from_env()

    running_node_names = _find_running_node_names(client)

    header = \
        "\nName"+(21*" ") + \
        "Status"+(10*" ") + \
        "System/User"

    click.echo(header)
    click.echo("-"*len(header))

    running = Fore.GREEN + "Running" + Style.RESET_ALL
    stopped = Fore.RED + "Not running" + Style.RESET_ALL

    # system folders
    configs, f1 = NodeContext.available_configurations(
        system_folders=True)
    for config in configs:
        status = running if f"{APPNAME}-{config.name}-system" in \
            running_node_names else stopped
        click.echo(
            f"{config.name:25}"
            f"{status:25}System "
        )

    # user folders
    configs, f2 = NodeContext.available_configurations(
        system_folders=False)
    for config in configs:
        status = running if f"{APPNAME}-{config.name}-user" in \
            running_node_names else stopped
        click.echo(
            f"{config.name:25}"
            f"{status:25}User   "
        )

    click.echo("-"*53)
    if len(f1)+len(f2):
        warning(
             f"{Fore.RED}Failed imports: {len(f1)+len(f2)}{Style.RESET_ALL}")


#
#   new
#
@cli_node.command(name="new")
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option('--system', 'system_folders', flag_value=True,
              help="Store this configuration in the system folders")
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL,
              help="Store this configuration in the user folders. This is the "
                   "default")
def cli_node_new_configuration(name: str, system_folders: bool) -> None:
    """
    Create a new node configuration.

    Checks if the configuration already exists. If this is not the case
    a questionnaire is invoked to create a new configuration file.
    """
    name = prompt_config_name(name)
    # check if config name is allowed docker name
    check_config_name_allowed(name)

    # check that this config does not exist
    if NodeContext.config_exists(name, system_folders):
        error(f"Configuration {name} already exists!")
        exit(1)

    # Check that we can write in this folder
    if not check_config_writeable(system_folders):
        error("Cannot write configuration file. Exiting...")
        exit(1)

    # create config in ctx location
    flag = "--system" if system_folders else ""
    cfg_file = configuration_wizard("node", name, system_folders)
    info(f"New configuration created: {Fore.GREEN}{cfg_file}{Style.RESET_ALL}")
    info(f"You can start the node by running "
         f"{Fore.GREEN}vnode start {flag}{Style.RESET_ALL}")


#
#   files
#
@cli_node.command(name="files")
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option('--system', 'system_folders', flag_value=True,
              help="Search for the configuration in the system folders")
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL,
              help="Search for the configuration in the user folders. This is "
                   "the default")
def cli_node_files(name: str, system_folders: bool) -> None:
    """
    Prints the location of important node files.

    If the specified configuration cannot be found, it exits. Otherwise
    it returns the absolute path to the output.
    """
    name = _select_node(name, system_folders)

    # create node context
    ctx = NodeContext(name, system_folders=system_folders)

    # return path of the configuration
    info(f"Configuration file = {ctx.config_file}")
    info(f"Log file           = {ctx.log_file}")
    info(f"data folders       = {ctx.data_dir}")
    info("Database labels and files")
    for db in ctx.databases:
        info(f" - {db['label']:15} = {db['uri']} (type: {db['type']})")


#
#   start
#
@cli_node.command(name='start')
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("-c", "--config", default=None,
              help='Absolute path to configuration-file; overrides NAME')
@click.option('--system', 'system_folders', flag_value=True,
              help="Search for the configuration in the system folders")
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL,
              help="Search for the configuration in the user folders. This is "
                   "the default")
@click.option('-i', '--image', default=None, help="Node Docker image to use")
@click.option('--keep/--auto-remove', default=False,
              help="Keep node container after finishing. Useful for debugging")
@click.option('--force-db-mount', is_flag=True,
              help="Always mount node databases; skip the check if they are "
                   "existing files.")
@click.option('--attach/--detach', default=False,
              help="Show node logs on the current console after starting the "
                   "node")
@click.option('--mount-src', default='',
              help="Override vantage6 source code in container with the source"
                   " code in this path")
def cli_node_start(name: str, config: str, system_folders: bool, image: str,
                   keep: bool, mount_src: str, attach: bool,
                   force_db_mount: bool) -> None:
    """
    Start the node.
    """
    vnode_start(name, config, system_folders, image, keep, mount_src, attach,
                force_db_mount)


def vnode_start(name: str, config: str, system_folders: bool,
                image: str, keep: bool, mount_src: str, attach: bool,
                force_db_mount: bool) -> None:
    """
    Start the node instance inside a Docker container.

    Parameters
    ----------
    name : str
        Name of the configuration file.
    config : str
        Absolute path to configuration-file; overrides NAME
    system_folders : bool
        Is this configuration stored in the system or in the user folders.
    image : str
        Node Docker image to use.
    keep : bool
        Keep container when finished or in the event of a crash. This is useful
        for debugging.
    mount_src : str
        Mount vantage6 package source that replaces the source inside the
        container. This is useful for debugging.
    attach : bool
        Attach node logs to the console after start.
    force_db_mount : bool
        Skip the check of the existence of the DB (always try to mount).
    """
    check_docker_running()
    info("Starting node...")
    info("Finding Docker daemon")
    docker_client = docker.from_env()
    NodeContext.LOGGING_ENABLED = False
    if config:
        name = Path(config).stem
        ctx = NodeContext(name, system_folders, config)

    else:
        # in case no name is supplied, ask the user to select one
        if not name:
            name = select_configuration_questionaire("node", system_folders)

        # check that config exists, if not a questionaire will be invoked
        if not NodeContext.config_exists(name, system_folders):
            warning(f"Configuration {Fore.RED}{name}{Style.RESET_ALL} does not"
                    " exist.")

            if q.confirm("Create this configuration now?").ask():
                configuration_wizard("node", name, system_folders)

            else:
                error("Config file couldn't be loaded")
                sys.exit(0)

        ctx = NodeContext(name, system_folders)

    # check if config name is allowed docker name, else exit
    check_config_name_allowed(ctx.name)

    # check that this node is not already running
    running_nodes = docker_client.containers.list(
        filters={"label": f"{APPNAME}-type=node"}
    )

    suffix = "system" if system_folders else "user"
    for node in running_nodes:
        if node.name == f"{APPNAME}-{name}-{suffix}":
            error(f"Node {Fore.RED}{name}{Style.RESET_ALL} is already running")
            exit(1)

    # make sure the (host)-task and -log dir exists
    info("Checking that data and log dirs exist")
    ctx.data_dir.mkdir(parents=True, exist_ok=True)
    ctx.log_dir.mkdir(parents=True, exist_ok=True)

    # Determine image-name. First we check if the option --image has been used.
    # Then we check if the image has been specified in the config file, and
    # finally we use the default settings from the package.
    if not image:
        custom_images: dict = ctx.config.get('images')
        if custom_images:
            image = custom_images.get("node")

        # if no custom image is specified, find the server version and use
        # the latest images from that minor version
        client = _create_client(ctx)
        major_minor = None
        try:
            # try to get server version, skip if can't get a connection
            version = client.util.get_server_version(
                attempts_on_timeout=3
            )['version']
            major_minor = '.'.join(version.split('.')[:2])
            image = (f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_NODE_IMAGE_WO_TAG}"
                     f":{major_minor}")
        except Exception:
            warning("Could not determine server version. Using default node "
                    "image")
            pass  # simply use the default image

        if major_minor and not __version__.startswith(major_minor):
            warning(
                "Version mismatch between CLI and server/node. CLI is running "
                f"on version {__version__}, while node and server are on "
                f"version {major_minor}. This might cause unexpected issues; "
                f"changing to {major_minor}.<latest> is recommended."
            )

        if not image:
            image = f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_NODE_IMAGE}"

    info(f"Pulling latest node image '{image}'")
    try:
        # docker_client.images.pull(image)
        pull_if_newer(docker.from_env(), image)

    except Exception as e:
        warning(' ... Getting latest node image failed:')
        warning(f"     {e}")
    else:
        info(" ... success!")

    info("Creating Docker data volume")

    data_volume = docker_client.volumes.create(ctx.docker_volume_name)
    vpn_volume = docker_client.volumes.create(ctx.docker_vpn_volume_name)
    ssh_volume = docker_client.volumes.create(ctx.docker_ssh_volume_name)
    squid_volume = docker_client.volumes.create(ctx.docker_squid_volume_name)

    info("Creating file & folder mounts")
    # FIXME: should obtain mount points from DockerNodeContext
    mounts = [
        # (target, source)
        ("/mnt/log", str(ctx.log_dir)),
        ("/mnt/data", data_volume.name),
        ("/mnt/vpn", vpn_volume.name),
        ("/mnt/ssh", ssh_volume.name),
        ("/mnt/squid", squid_volume.name),
        ("/mnt/config", str(ctx.config_dir)),
        ("/var/run/docker.sock", "/var/run/docker.sock"),
    ]

    if mount_src:
        # If mount_src is a relative path, docker will consider it a volume.
        mount_src = os.path.abspath(mount_src)
        mounts.append(('/vantage6', mount_src))

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

    # Mount private keys for ssh tunnels
    ssh_tunnels = ctx.config.get("ssh-tunnels", [])
    for ssh_tunnel in ssh_tunnels:
        hostname = ssh_tunnel.get("hostname")
        key_path = ssh_tunnel.get("ssh", {}).get("identity", {}).get("key")
        if not key_path:
            error(f"SSH tunnel identity {Fore.RED}{hostname}{Style.RESET_ALL} "
                  "key not provided. Continuing to start without this tunnel.")
        key_path = Path(key_path)
        if not key_path.exists():
            error(f"SSH tunnel identity {Fore.RED}{hostname}{Style.RESET_ALL} "
                  "key does not exist. Continuing to start without this "
                  "tunnel.")

        info(f"  Mounting private key for {hostname} at {key_path}")

        # we remove the .tmp in the container, this is because the file is
        # mounted in a volume mount point. Somehow the file is than empty in
        # the volume but not for the node instance. By removing the .tmp we
        # make sure that the file is not empty in the volume.
        mounts.append((f"/mnt/ssh/{hostname}.pem.tmp", str(key_path)))

    env = {
        "DATA_VOLUME_NAME": data_volume.name,
        "VPN_VOLUME_NAME": vpn_volume.name,
        "PRIVATE_KEY": "/mnt/private_key.pem"
    }

    # only mount the DB if it is a file
    info("Setting up databases")
    db_labels = [db['label'] for db in ctx.databases]
    for label in db_labels:

        db_config = get_database_config(ctx.databases, label)
        uri = db_config['uri']
        db_type = db_config['type']

        info(f"  Processing {Fore.GREEN}{db_type}{Style.RESET_ALL} database "
             f"{Fore.GREEN}{label}:{uri}{Style.RESET_ALL}")
        label_capitals = label.upper()

        try:
            file_based = Path(uri).exists()
        except Exception:
            # If the database uri cannot be parsed, it is definitely not a
            # file. In case of http servers or sql servers, checking the path
            # of the the uri will lead to an OS-dependent error, which is why
            # we catch all exceptions here.
            file_based = False

        if not file_based and not force_db_mount:
            debug('  - non file-based database added')
            env[f'{label_capitals}_DATABASE_URI'] = uri
        else:
            debug('  - file-based database added')
            suffix = Path(uri).suffix
            env[f'{label_capitals}_DATABASE_URI'] = f'{label}{suffix}'
            mounts.append((f'/mnt/{label}{suffix}', str(uri)))

    system_folders_option = "--system" if system_folders else "--user"
    cmd = f'vnode-local start -c /mnt/config/{name}.yaml -n {name} '\
          f' --dockerized {system_folders_option}'

    info("Running Docker container")
    volumes = []
    for mount in mounts:
        volumes.append(f'{mount[1]}:{mount[0]}')

    remove_container_if_exists(
        docker_client=docker_client, name=ctx.docker_container_name
    )

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

    info(f"Success! container id = {container}")

    if attach:
        logs = container.attach(stream=True, logs=True)
        Thread(target=_print_log_worker, args=(logs,), daemon=True).start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                info("Closing log file. Keyboard Interrupt.")
                info("Note that your node is still running! Shut it down with "
                     f"'{Fore.RED}vnode stop{Style.RESET_ALL}'")
                exit(0)


#
#   stop
#
@cli_node.command(name='stop')
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option('--system', 'system_folders', flag_value=True,
              help="Search for configuration in system folders instead of "
                   "user folders")
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL,
              help="Search for configuration in the user folders instead of "
                   "system folders. This is the default.")
@click.option('--all', 'all_nodes', flag_value=True,
              help="Stop all running nodes")
@click.option('--force', 'force', flag_value=True,
              help="Kill nodes instantly; don't wait for them to shut down")
def cli_node_stop(name: str, system_folders: bool, all_nodes: bool,
                  force: bool) -> None:
    """
    Stop one or all running nodes.
    """
    vnode_stop(name, system_folders, all_nodes, force)


def vnode_stop(name: str, system_folders: bool, all_nodes: bool,
               force: bool) -> None:
    """
    Stop a running node container.

    Parameters
    ----------
    name : str
        Name of the configuration file.
    system_folders : bool
        Is this configuration stored in the system or in the user folders.
    all_nodes : bool
        If set to true, all running nodes will be stopped.
    force : bool
        If set to true, the node will not be stopped gracefully.
    """
    check_docker_running()
    client = docker.from_env()

    running_node_names = _find_running_node_names(client)

    if not running_node_names:
        warning("No nodes are currently running.")
        return

    if force:
        warning('Forcing the node to stop will not terminate helper '
                'containers, neither will it remove routing rules made on the '
                'host!')

    if all_nodes:
        for name in running_node_names:
            container = client.containers.get(name)
            if force:
                container.kill()
            else:
                container.stop()
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
            # Stop the container. Using stop() gives the container 10s to exit
            # itself, if not then it will be killed
            if force:
                container.kill()
            else:
                container.stop()
            info(f"Stopped the {Fore.GREEN}{name}{Style.RESET_ALL} Node.")
        else:
            error(f"{Fore.RED}{name}{Style.RESET_ALL} is not running?")


#
#   attach
#
@cli_node.command(name='attach')
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option('--system', 'system_folders', flag_value=True,
              help="Search for configuration in system folders rather than "
                   "user folders")
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL,
              help="Search for configuration in user folders rather than "
                   "system folders. This is the default")
def cli_node_attach(name: str, system_folders: bool) -> None:
    """
    Show the node logs in the current console.
    """
    check_docker_running()
    client = docker.from_env()

    running_node_names = _find_running_node_names(client)

    if not running_node_names:
        warning("No nodes are currently running. Cannot show any logs!")
        return

    if not name:
        name = q.select("Select the node you wish to inspect:",
                        choices=running_node_names).ask()
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}"

    if name in running_node_names:
        container = client.containers.get(name)
        logs = container.attach(stream=True, logs=True)
        Thread(target=_print_log_worker, args=(logs,), daemon=True).start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                info("Closing log file. Keyboard Interrupt.")
                info("Note that your node is still running! Shut it down with "
                     f"'{Fore.RED}vnode stop{Style.RESET_ALL}'")
                exit(0)
    else:
        error(f"{Fore.RED}{name}{Style.RESET_ALL} was not running!?")


#
#   create-private-key
#
@cli_node.command(name='create-private-key')
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("-c", "--config", default=None,
              help='Absolute path to configuration-file; overrides NAME')
@click.option('--system', 'system_folders', flag_value=True,
              help="Search for configuration in system folders rather than "
                   "user folders")
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL,
              help="Search for configuration in user folders rather than "
                   "system folders. This is the default")
@click.option('--no-upload', 'upload', flag_value=False, default=True,
              help="Don't upload the public key to the server")
@click.option("-o", "--organization-name", default=None,
              help="Organization name. Used in the filename of the private key"
                   " so that it can easily be recognized again later")
@click.option('--overwrite', 'overwrite', flag_value=True, default=False,
              help="Overwrite existing private key if present")
def cli_node_create_private_key(
        name: str, config: str, system_folders: bool, upload: bool,
        organization_name: str, overwrite: bool) -> None:
    """
    Create and upload a new private key

    Use this command with caution! Uploading a new key has several
    consequences, e.g. you and other users of your organization
    will no longer be able to read the results of tasks encrypted with current
    key.
    """
    NodeContext.LOGGING_ENABLED = False
    if config:
        name = Path(config).stem
        ctx = NodeContext(name, system_folders, config)
    else:
        # retrieve context
        name = _select_node(name, system_folders)

        # raise error if config could not be found
        if not NodeContext.config_exists(name, system_folders):
            error(
                f"The configuration {Fore.RED}{name}{Style.RESET_ALL} could "
                "not be found."
            )
            exit(1)

        # Create node context
        ctx = NodeContext(name, system_folders)

    # Authenticate with the server to obtain organization name if it wasn't
    # provided
    if organization_name is None:
        client = _create_client_and_authenticate(ctx)
        organization_name = client.whoami.organization_name

    # create directory where private key goes if it doesn't exist yet
    ctx.type_data_folder(system_folders).mkdir(parents=True, exist_ok=True)

    # generate new key, and save it
    filename = f"privkey_{organization_name}.pem"
    file_ = ctx.type_data_folder(system_folders) / filename

    if file_.exists():
        warning(f"File '{Fore.CYAN}{file_}{Style.RESET_ALL}' exists!")

        if overwrite:
            warning("'--override' specified, so it will be overwritten ...")

    if file_.exists() and not overwrite:
        error("Could not create private key!")
        warning(
            "If you're **sure** you want to create a new key, "
            "please run this command with the '--overwrite' flag"
        )
        warning("Continuing with existing key instead!")
        private_key = RSACryptor(file_).private_key

    else:
        try:
            info("Generating new private key")
            private_key = RSACryptor.create_new_rsa_key(file_)

        except Exception as e:
            error(f"Could not create new private key '{file_}'!?")
            debug(e)
            info("Bailing out ...")
            exit(1)

        warning(f"Private key written to '{file_}'")
        warning(
            "If you're running multiple nodes, be sure to copy the private "
            "key to the appropriate directories!"
        )

    # create public key
    info("Deriving public key")
    public_key = RSACryptor.create_public_key_bytes(private_key)

    # update config file
    info("Updating configuration")
    ctx.config["encryption"]["private_key"] = str(file_)
    ctx.config_manager.put(ctx.config)
    ctx.config_manager.save(ctx.config_file)

    # upload key to the server
    if upload:
        info(
            "Uploading public key to the server. "
            "This will overwrite any previously existing key!"
        )

        if 'client' not in locals():
            client = _create_client_and_authenticate(ctx)

        # TODO what happens if the user doesn't have permission to upload key?
        # Does that lead to an exception or not?
        try:
            client.request(
                f"/organization/{client.whoami.organization_id}",
                method="patch",
                json={"public_key": bytes_to_base64s(public_key)}
            )

        except Exception as e:
            error("Could not upload the public key!")
            debug(e)
            exit(1)

    else:
        warning("Public key not uploaded!")

    info("[Done]")


#
#   clean
#
@cli_node.command(name='clean')
def cli_node_clean() -> None:
    """
    Erase temporary Docker volumes.
    """
    check_docker_running()
    client = docker.from_env()

    # retrieve all volumes
    volumes = client.volumes.list()
    candidates = []
    msg = "This would remove the following volumes: "
    for volume in volumes:
        if volume.name[-6:] == "tmpvol":
            candidates.append(volume)
            msg += volume.name + ","
    info(msg)

    confirm = q.confirm("Are you sure?")
    if confirm.ask():
        for volume in candidates:
            try:
                volume.remove()
                # info(volume.name)
            except docker.errors.APIError as e:
                error(f"Failed to remove volume {Fore.RED}'{volume.name}'"
                      f"{Style.RESET_ALL}. Is it still in use?")
                debug(e)
                exit(1)
    info("Done!")


#
#   remove
#
@cli_node.command(name="remove")
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option('--system', 'system_folders', flag_value=True,
              help="Search for configuration in system folders rather than "
                   "user folders")
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL,
              help="Search for configuration in user folders rather than "
                   "system folders. This is the default")
@click.option('-f', "--force", type=bool, flag_value=True,
              help='Don\'t ask for confirmation')
def cli_node_remove(name: str, system_folders: bool, force: bool) -> None:
    """
    Delete a node permanently.

    Remove the configuration file, log file, and docker volumes attached to
    the node.
    """
    vnode_remove(name, system_folders, force)


def vnode_remove(name: str, system_folders: bool, force: bool):
    """
    Delete a node permanently

    * if the node is still running, exit and tell user to run vnode stop first
    * remove configuration file
    * remove log file
    * remove docker volumes attached to the node

    Parameters
    ----------
    name : str
        Configuration name
    system_folders : bool
        If True, use system folders, otherwise use user folders
    force : bool
        If True, don't ask for confirmation before removing the node
    """
    # select configuration name if none supplied
    name = _select_node(name, system_folders)

    client = docker.from_env()
    check_if_docker_daemon_is_running(client)

    # check if node is still running, otherwise don't allow deleting it
    running_node_names = _find_running_node_names(client)

    post_fix = "system" if system_folders else "user"
    node_container_name = f"{APPNAME}-{name}-{post_fix}"
    if node_container_name in running_node_names:
        error(f"Node {name} is still running! Please stop the node before "
              "deleting it.")
        exit(1)

    if not force:
        if not q.confirm(
            "This node will be deleted permanently including its "
            "configuration. Are you sure?", default=False
        ).ask():
            info("Node will not be deleted")
            exit(0)

    # create node context
    ctx = NodeContext(name, system_folders=system_folders)

    # remove the docker volume and any temporary volumes
    debug("Deleting docker volumes")
    volumes = client.volumes.list()
    for vol in volumes:
        if vol.name.startswith(ctx.docker_volume_name):  # includes tmp volumes
            info(f"Deleting docker volume {vol.name}")
            vol.remove()
        # remove docker vpn volume
        if vol.name == ctx.docker_vpn_volume_name:
            info(f"Deleting VPN docker volume {vol.name}")
            vol.remove()

    # remove the VPN configuration file
    vpn_config_file = os.path.join(ctx.data_dir, 'vpn', VPN_CONFIG_FILE)
    remove_file(vpn_config_file, 'VPN configuration')

    # remove the config file
    remove_file(ctx.config_file, 'configuration')

    # remove the log file. As this process opens the log file above, the log
    # handlers need to be closed before deleting
    info(f"Removing log file {ctx.log_file}")
    for handler in itertools.chain(ctx.log.handlers, ctx.log.root.handlers):
        handler.close()
    # remove_file(ctx.log_file, 'log')

    # removes the whole folder
    rmtree(Path(ctx.log_file.parent))

    # remove the folder: if it hasn't been started yet this won't exist...
    if Path.exists(ctx.config_dir / name):
        rmtree(ctx.config_dir / name)


#
#   version
#
@cli_node.command(name='version')
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option('--system', 'system_folders', flag_value=True,
              help="Search for configuration in system folders rather than "
                   "user folders")
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL,
              help="Search for configuration in user folders rather than "
                   "system folders. This is the default")
def cli_node_version(name: str, system_folders: bool) -> None:
    """
    Returns current version of a vantage6 node.
    """
    check_docker_running()
    client = docker.from_env()

    running_node_names = _find_running_node_names(client)

    if not name:
        if not running_node_names:
            error("No nodes are running! You can only check the version for "
                  "nodes that are running")
            exit(1)
        name = q.select("Select the node you wish to inspect:",
                        choices=running_node_names).ask()
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}"

    if name in running_node_names:
        container = client.containers.get(name)
        version = container.exec_run(cmd='vnode-local version', stdout=True)
        click.echo(
            {"node": version.output.decode('utf-8'), "cli": __version__})
    else:
        error(f"Node {name} is not running! Cannot provide version...")


#
#   set-api-key
#
@cli_node.command(name='set-api-key')
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--api-key", default=None, help="New API key")
@click.option('--system', 'system_folders', flag_value=True,
              help="Search for configuration in system folders rather than "
                   "user folders")
@click.option('--user', 'system_folders', flag_value=False, default=N_FOL,
              help="Search for configuration in user folders rather than "
                   "system folders. This is the default")
def cli_node_set_api_key(name: str, api_key: str,
                         system_folders: bool) -> None:
    """
    Put a new API key into the node configuration file
    """
    # select node name
    name = _select_node(name, system_folders)

    # Check that we can write in the config folder
    if not check_config_writeable(system_folders):
        error("Your user does not have write access to all folders. Exiting")
        exit(1)

    if not api_key:
        api_key = q.text("Please enter your new API key:").ask()

    # get configuration manager
    ctx = NodeContext(name, system_folders=system_folders)
    conf_mgr = NodeConfigurationManager.from_file(ctx.config_file)

    # set new api key, and save the file
    ctx.config['api_key'] = api_key
    conf_mgr.put(ctx.config)
    conf_mgr.save(ctx.config_file)
    info("Your new API key has been uploaded to the config file "
         f"{ctx.config_file}.")


#  helper functions
def _print_log_worker(logs_stream: Iterable[bytes]) -> None:
    """
    Print the logs from the logs stream.

    Parameters
    ----------
    logs_stream : Iterable[bytes]
        Output of the container.attach() method
    """
    for log in logs_stream:
        print(log.decode(STRING_ENCODING), end="")


def _create_client(ctx: NodeContext) -> UserClient:
    """
    Create a client instance.

    Parameters
    ----------
    ctx : NodeContext
        Context of the node loaded from the configuration file
    Returns
    -------
    UserClient
        vantage6 client
    """
    host = ctx.config['server_url']
    # if the server is run locally, we need to use localhost here instead of
    # the host address of docker
    if host in ['http://host.docker.internal', 'http://172.17.0.1']:
        host = 'http://localhost'
    port = ctx.config['port']
    api_path = ctx.config['api_path']
    info(f"Connecting to server at '{host}:{port}{api_path}'")
    return UserClient(host, port, api_path, log_level='warn')


def _create_client_and_authenticate(ctx: NodeContext) -> UserClient:
    """
    Generate a client and authenticate with the server.

    Parameters
    ----------
    ctx : NodeContext
        Context of the node loaded from the configuration file

    Returns
    -------
    UserClient
        vantage6 client
    """
    client = _create_client(ctx)

    username = q.text("Username:").ask()
    password = q.password("Password:").ask()

    try:
        client.authenticate(username, password)

    except Exception as exc:
        error("Could not authenticate with server!")
        debug(exc)
        exit(1)

    return client


def _select_node(name: str, system_folders: bool) -> tuple[str, str]:
    """
    Let user select node through questionnaire if name is not given.

    Returns
    -------
    str
        Name of the configuration file
    """
    name = name if name else \
        select_configuration_questionaire("node", system_folders)

    # raise error if config could not be found
    if not NodeContext.config_exists(name, system_folders):
        error(
            f"The configuration {Fore.RED}{name}{Style.RESET_ALL} could "
            f"not be found."
        )
        exit(1)
    return name


def _find_running_node_names(client: docker.DockerClient) -> list[str]:
    """
    Returns a list of names of running nodes.

    Parameters
    ----------
    client : docker.DockerClient
        Docker client instance

    Returns
    -------
    list[str]
        List of names of running nodes
    """
    running_nodes = client.containers.list(
        filters={"label": f"{APPNAME}-type=node"})
    return [node.name for node in running_nodes]
