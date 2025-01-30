import click
import docker
from docker.client import DockerClient

from vantage6.common import info, warning, error
from vantage6.common.docker.network_manager import NetworkManager
from vantage6.common.globals import (
    APPNAME,
    DEFAULT_SERVER_IMAGE,
    DEFAULT_UI_IMAGE,
    InstanceType,
)

from vantage6.common.globals import Ports
from vantage6.cli.context.server import ServerContext
from vantage6.cli.rabbitmq.queue_manager import RabbitMQManager
from vantage6.cli.server.common import stop_ui
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    attach_logs,
    check_for_start,
    get_image,
    mount_database,
    mount_source,
    pull_infra_image,
)


@click.command()
@click.option("--ip", default=None, help="IP address to listen on")
@click.option("-p", "--port", default=None, type=int, help="Port to listen on")
@click.option("-i", "--image", default=None, help="Server Docker image to use")
@click.option(
    "--with-ui",
    "start_ui",
    flag_value=True,
    default=False,
    help="Start the graphical User Interface as well",
)
@click.option(
    "--ui-port", default=None, type=int, help="Port to listen on for the User Interface"
)
@click.option(
    "--with-rabbitmq",
    "start_rabbitmq",
    flag_value=True,
    default=False,
    help="Start RabbitMQ message broker as local "
    "container - use in development only",
)
@click.option("--rabbitmq-image", default=None, help="RabbitMQ docker image to use")
@click.option(
    "--keep/--auto-remove",
    default=False,
    help="Keep image after server has stopped. Useful for debugging",
)
@click.option(
    "--mount-src",
    default="",
    help="Override vantage6 source code in container with the source"
    " code in this path",
)
@click.option(
    "--attach/--detach",
    default=False,
    help="Print server logs to the console after start",
)
@click_insert_context(type_="server")
def cli_server_start(
    ctx: ServerContext,
    ip: str,
    port: int,
    image: str,
    start_ui: bool,
    ui_port: int,
    start_rabbitmq: bool,
    rabbitmq_image: str,
    keep: bool,
    mount_src: str,
    attach: bool,
) -> None:
    """
    Start the server.
    """
    info("Starting server...")
    docker_client = check_for_start(ctx, InstanceType.SERVER)

    image = get_image(image, ctx, "server", DEFAULT_SERVER_IMAGE)

    # check that log directory exists - or create it
    ctx.log_dir.mkdir(parents=True, exist_ok=True)

    info("Pulling server image...")
    pull_infra_image(docker_client, image, InstanceType.SERVER)

    info("Creating mounts")
    config_file = "/mnt/config.yaml"
    mounts = [
        docker.types.Mount(config_file, str(ctx.config_file), type="bind"),
        docker.types.Mount("/mnt/log/", str(ctx.log_dir), type="bind"),
    ]

    src_mount = mount_source(mount_src)
    if src_mount:
        mounts.append(src_mount)

    mount, environment_vars = mount_database(ctx, InstanceType.SERVER)
    if mount:
        mounts.append(mount)

    # Create a docker network for the server and other services like RabbitMQ
    # to reside in
    server_network_mgr = NetworkManager(
        network_name=f"{APPNAME}-{ctx.name}-{ctx.scope}-network"
    )
    server_network_mgr.create_network(is_internal=False)

    if (
        start_rabbitmq
        or ctx.config.get("rabbitmq")
        and ctx.config["rabbitmq"].get("start_with_server", False)
    ):
        # Note that ctx.data_dir has been created at this point, which is
        # required for putting some RabbitMQ configuration files inside
        info("Starting RabbitMQ container")
        _start_rabbitmq(ctx, rabbitmq_image, server_network_mgr)
    elif ctx.config.get("rabbitmq"):
        info(
            "RabbitMQ is provided in the config file as external service. "
            "Assuming this service is up and running."
        )
    else:
        warning(
            "Message queue is not set up! This means that the vantage6 server "
            "cannot be scaled horizontally!"
        )

    # start the UI if requested
    if start_ui or ctx.config.get("ui") and ctx.config["ui"].get("enabled"):
        _start_ui(docker_client, ctx, ui_port)

    # The `ip` and `port` refer here to the ip and port within the container.
    # So we do not really care that is it listening on all interfaces.
    internal_port = 5000
    cmd = (
        f"uwsgi --http :{internal_port} --gevent 1000 --http-websockets "
        "--master --callable app --disable-logging "
        "--wsgi-file /vantage6/vantage6-server/vantage6/server/wsgi.py "
        f"--pyargv {config_file}"
    )
    info(cmd)

    info("Run Docker container")
    port_ = str(port or ctx.config["port"] or Ports.DEV_SERVER.value)
    container = docker_client.containers.run(
        image,
        command=cmd,
        mounts=mounts,
        detach=True,
        labels={f"{APPNAME}-type": InstanceType.SERVER, "name": ctx.config_file_name},
        environment=environment_vars,
        ports={f"{internal_port}/tcp": (ip, port_)},
        name=ctx.docker_container_name,
        auto_remove=not keep,
        tty=True,
        network=server_network_mgr.network_name,
    )

    info(f"Success! container id = {container.id}")

    if attach:
        attach_logs(container, InstanceType.SERVER)


def _start_rabbitmq(
    ctx: ServerContext, rabbitmq_image: str, network_mgr: NetworkManager
) -> None:
    """
    Start the RabbitMQ container if it is not already running.

    Parameters
    ----------
    ctx : ServerContext
        Server context object
    rabbitmq_image : str
        RabbitMQ image to use
    network_mgr : NetworkManager
        Network manager object
    """
    rabbit_uri = ctx.config["rabbitmq"].get("uri")
    if not rabbit_uri:
        error(
            "No RabbitMQ URI found in the configuration file! Please add"
            "a 'uri' key to the 'rabbitmq' section of the configuration."
        )
        exit(1)
    # kick off RabbitMQ container
    rabbit_mgr = RabbitMQManager(ctx=ctx, network_mgr=network_mgr, image=rabbitmq_image)
    rabbit_mgr.start()


def _start_ui(client: DockerClient, ctx: ServerContext, ui_port: int) -> None:
    """
    Start the UI container.

    Parameters
    ----------
    client : DockerClient
        Docker client
    ctx : ServerContext
        Server context object
    ui_port : int
        Port to expose the UI on
    """
    # if no port is specified, check if config contains a port
    ui_config = ctx.config.get("ui")
    if ui_config and not ui_port:
        ui_port = ui_config.get("port")

    # check if the port is valid
    # TODO make function to check if port is valid, and use in more places
    if not isinstance(ui_port, int) or not 0 < ui_port < 65536:
        warning(
            f"UI port '{ui_port}' is not valid! Using default port "
            f"{Ports.DEV_UI.value}"
        )
        ui_port = str(Ports.DEV_UI.value)

    # find image to use
    image = get_image(None, ctx, "ui", DEFAULT_UI_IMAGE)

    pull_infra_image(client, image, InstanceType.UI)

    # set environment variables
    env_vars = {
        "SERVER_URL": f"http://localhost:{ctx.config.get('port')}",
        "API_PATH": ctx.config.get("api_path"),
    }

    # stop the UI container if it is already running
    stop_ui(client, ctx)

    info(f"Starting User Interface at port {ui_port}")
    ui_container_name = f"{APPNAME}-{ctx.name}-{ctx.scope}-ui"
    client.containers.run(
        image,
        detach=True,
        labels={f"{APPNAME}-type": "ui", "name": ctx.config_file_name},
        ports={"80/tcp": (ctx.config.get("ip"), ui_port)},
        name=ui_container_name,
        environment=env_vars,
        tty=True,
    )
