from pathlib import Path
from threading import Thread
import time
import os.path

import click
import docker

from colorama import Fore, Style

from vantage6.cli.common.start import pull_infra_image
from vantage6.common import warning, error, info, debug, get_database_config
from vantage6.common.globals import (
    APPNAME,
    DEFAULT_DOCKER_REGISTRY,
    DEFAULT_NODE_IMAGE,
    DEFAULT_NODE_IMAGE_WO_TAG,
    InstanceType,
)
from vantage6.common.docker.addons import (
    remove_container_if_exists,
    check_docker_running,
)

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context.node import NodeContext
from vantage6.cli.common.utils import print_log_worker
from vantage6.cli.node.common import create_client
from vantage6.cli.utils import check_config_name_allowed
from vantage6.cli import __version__


@click.command()
@click.option("-i", "--image", default=None, help="Node Docker image to use")
@click.option(
    "--keep/--auto-remove",
    default=False,
    help="Keep node container after finishing. Useful for debugging",
)
@click.option(
    "--force-db-mount",
    is_flag=True,
    help="Always mount node databases; skip the check if they are " "existing files.",
)
@click.option(
    "--attach/--detach",
    default=False,
    help="Show node logs on the current console after starting the " "node",
)
@click.option(
    "--mount-src",
    default="",
    help="Override vantage6 source code in container with the source"
    " code in this path",
)
@click_insert_context(InstanceType.NODE, include_name=True, include_system_folders=True)
def cli_node_start(
    ctx: NodeContext,
    name: str,
    system_folders: bool,
    image: str,
    keep: bool,
    mount_src: str,
    attach: bool,
    force_db_mount: bool,
) -> None:
    """
    Start the node.
    """
    check_docker_running()
    info("Starting node...")
    info("Finding Docker daemon")
    docker_client = docker.from_env()
    NodeContext.LOGGING_ENABLED = False

    # check if config name is allowed docker name, else exit
    check_config_name_allowed(ctx.name)

    # check that this node is not already running
    running_nodes = docker_client.containers.list(
        filters={"label": f"{APPNAME}-type={InstanceType.NODE}"}
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
        custom_images: dict = ctx.config.get("images")
        if custom_images:
            image = custom_images.get("node")
        else:
            # if no custom image is specified, find the server version and use
            # the latest images from that minor version
            client = create_client(ctx)
            major_minor = None
            try:
                # try to get server version, skip if can't get a connection
                version = client.util.get_server_version(attempts_on_timeout=3)[
                    "version"
                ]
                major_minor = ".".join(version.split(".")[:2])
                image = (
                    f"{DEFAULT_DOCKER_REGISTRY}/"
                    f"{DEFAULT_NODE_IMAGE_WO_TAG}"
                    f":{major_minor}"
                )
            except Exception:
                warning(
                    "Could not determine server version. Using default " "node image"
                )

            if major_minor and not __version__.startswith(major_minor):
                warning(
                    "Version mismatch between CLI and server/node. CLI is "
                    f"running on version {__version__}, while node and server "
                    f"are on version {major_minor}. This might cause "
                    f"unexpected issues; changing to {major_minor}.<latest> "
                    "is recommended."
                )

        # fail safe, in case no custom image is specified and we can't get the
        # server version
        if not image:
            image = f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_NODE_IMAGE}"

    info(f"Pulling latest node image '{image}'")
    pull_infra_image(docker_client, image, InstanceType.NODE)

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
        mounts.append(("/vantage6", mount_src))

    # FIXME: Code duplication: Node.__init__() (vantage6/node/__init__.py)
    #   uses a lot of the same logic. Suggest moving this to
    #   ctx.get_private_key()
    filename = ctx.config.get("encryption", {}).get("private_key")
    # filename may be set to an empty string
    if not filename:
        filename = "private_key.pem"

    # Location may be overridden by the environment
    filename = os.environ.get("PRIVATE_KEY", filename)

    # If ctx.get_data_file() receives an absolute path, it is returned as-is
    fullpath = Path(ctx.get_data_file(filename))
    if fullpath:
        if Path(fullpath).exists():
            mounts.append(("/mnt/private_key.pem", str(fullpath)))
        else:
            warning(f"Private key file is provided {fullpath}, but does not exist")

    # Mount private keys for ssh tunnels
    ssh_tunnels = ctx.config.get("ssh-tunnels", [])
    for ssh_tunnel in ssh_tunnels:
        hostname = ssh_tunnel.get("hostname")
        key_path = ssh_tunnel.get("ssh", {}).get("identity", {}).get("key")
        if not key_path:
            error(
                f"SSH tunnel identity {Fore.RED}{hostname}{Style.RESET_ALL} "
                "key not provided. Continuing to start without this tunnel."
            )
        key_path = Path(key_path)
        if not key_path.exists():
            error(
                f"SSH tunnel identity {Fore.RED}{hostname}{Style.RESET_ALL} "
                "key does not exist. Continuing to start without this "
                "tunnel."
            )

        info(f"  Mounting private key for {hostname} at {key_path}")

        # we remove the .tmp in the container, this is because the file is
        # mounted in a volume mount point. Somehow the file is than empty in
        # the volume but not for the node instance. By removing the .tmp we
        # make sure that the file is not empty in the volume.
        mounts.append((f"/mnt/ssh/{hostname}.pem.tmp", str(key_path)))

    env = {
        "DATA_VOLUME_NAME": data_volume.name,
        "VPN_VOLUME_NAME": vpn_volume.name,
        "PRIVATE_KEY": "/mnt/private_key.pem",
    }

    # only mount the DB if it is a file
    info("Setting up databases")
    db_labels = [db["label"] for db in ctx.databases]
    for label in db_labels:
        # check that label contains only valid characters
        if not label.isidentifier():
            error(
                f"Database label {Fore.RED}{label}{Style.RESET_ALL} contains"
                " invalid characters. Only letters, numbers, and underscores"
                " are allowed, and it cannot start with a number."
            )
            exit(1)

        db_config = get_database_config(ctx.databases, label)
        uri = db_config["uri"]
        db_type = db_config["type"]

        info(
            f"  Processing {Fore.GREEN}{db_type}{Style.RESET_ALL} database "
            f"{Fore.GREEN}{label}:{uri}{Style.RESET_ALL}"
        )
        label_capitals = label.upper()

        try:
            db_file_exists = Path(uri).exists()
        except Exception:
            # If the database uri cannot be parsed, it is definitely not a
            # file. In case of http servers or sql servers, checking the path
            # of the the uri will lead to an OS-dependent error, which is why
            # we catch all exceptions here.
            db_file_exists = False

        if db_type in ["folder", "csv", "parquet", "excel"] and not db_file_exists:
            error(
                f"Database {Fore.RED}{uri}{Style.RESET_ALL} not found. Databases of "
                f"type '{db_type}' must be present on the harddrive. Please update "
                "your node configuration file."
            )
            exit(1)

        if not db_file_exists and not force_db_mount:
            debug("  - non file-based database added")
            env[f"{label_capitals}_DATABASE_URI"] = uri
        else:
            debug("  - file-based database added")
            suffix = Path(uri).suffix
            env[f"{label_capitals}_DATABASE_URI"] = f"{label}{suffix}"
            mounts.append((f"/mnt/{label}{suffix}", str(uri)))

    system_folders_option = "--system" if system_folders else "--user"
    cmd = (
        f"vnode-local start -c /mnt/config/{name}.yaml -n {name} "
        f" --dockerized {system_folders_option}"
    )

    volumes = []
    for mount in mounts:
        volumes.append(f"{mount[1]}:{mount[0]}")

    extra_mounts = ctx.config.get("node_extra_mounts", [])
    for mount in extra_mounts:
        volumes.append(mount)

    extra_env = ctx.config.get("node_extra_env", {})
    # all extra env var names should be valid identifiers
    extra_env_invalid = [key for key in extra_env.keys() if not key.isidentifier()]
    if extra_env_invalid:
        error(
            "Environment variable names should be valid identifiers. "
            f"The following break this rule: {extra_env_invalid}"
        )
        exit(1)
    # we won't accept overwrites of existing env vars
    env_overwrites = extra_env.keys() & env.keys()
    if env_overwrites:
        error(
            "Cannot overwrite existing node environment variables: " f"{env_overwrites}"
        )
        exit(1)
    env.update(extra_env)

    # Add extra hosts to the environment
    extra_hosts = ctx.config.get("node_extra_hosts", {})

    remove_container_if_exists(
        docker_client=docker_client, name=ctx.docker_container_name
    )

    info("Running Docker container")
    container = docker_client.containers.run(
        image,
        command=cmd,
        volumes=volumes,
        detach=True,
        labels={
            f"{APPNAME}-type": InstanceType.NODE,
            "system": str(system_folders),
            "name": ctx.config_file_name,
        },
        environment=env,
        name=ctx.docker_container_name,
        auto_remove=not keep,
        tty=True,
        extra_hosts=extra_hosts,
    )

    info("Node container was started!")
    info(
        "Please check the node logs to see if the node successfully connects to the "
        "server."
    )

    if attach:
        logs = container.attach(stream=True, logs=True)
        Thread(target=print_log_worker, args=(logs,), daemon=True).start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                info("Closing log file. Keyboard Interrupt.")
                info(
                    "Note that your node is still running! Shut it down with "
                    f"'{Fore.RED}v6 node stop{Style.RESET_ALL}'"
                )
                exit(0)
    else:
        info(
            f"To see the logs, run: {Fore.GREEN}v6 node attach --name "
            f"{ctx.name}{Style.RESET_ALL}"
        )
