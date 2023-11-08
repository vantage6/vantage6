import os
from threading import Thread
import time

import click
import docker
from colorama import (Fore, Style)
from sqlalchemy.engine.url import make_url
from docker.client import DockerClient

from vantage6.common import info, warning, error
from vantage6.common.docker.addons import (
    pull_if_newer, check_docker_running
)
from vantage6.common.docker.network_manager import NetworkManager
from vantage6.common.globals import (
    APPNAME,
    DEFAULT_DOCKER_REGISTRY,
    DEFAULT_SERVER_IMAGE,
    DEFAULT_UI_IMAGE
)

from vantage6.cli.globals import DEFAULT_UI_PORT
from vantage6.cli.context import ServerContext
from vantage6.cli.utils import check_config_name_allowed
from vantage6.cli.rabbitmq.queue_manager import RabbitMQManager
from vantage6.cli.server.common import (
    click_insert_context, print_log_worker, stop_ui
)


@click.command()
@click.option('--ip', default=None, help='IP address to listen on')
@click.option('-p', '--port', default=None, type=int, help='Port to listen on')
@click.option('-i', '--image', default=None, help="Server Docker image to use")
@click.option('--with-ui', 'start_ui', flag_value=True, default=False,
              help="Start the graphical User Interface as well")
@click.option('--ui-port', default=None, type=int,
              help="Port to listen on for the User Interface")
@click.option('--with-rabbitmq', 'start_rabbitmq', flag_value=True,
              default=False, help="Start RabbitMQ message broker as local "
              "container - use in development only")
@click.option('--rabbitmq-image', default=None,
              help="RabbitMQ docker image to use")
@click.option('--keep/--auto-remove', default=False,
              help="Keep image after server has stopped. Useful for debugging")
@click.option('--mount-src', default='',
              help="Override vantage6 source code in container with the source"
              " code in this path")
@click.option('--attach/--detach', default=False,
              help="Print server logs to the console after start")
@click_insert_context
def cli_server_start(ctx: ServerContext, ip: str, port: int, image: str,
                     start_ui: bool, ui_port: int, start_rabbitmq: bool,
                     rabbitmq_image: str, keep: bool, mount_src: str,
                     attach: bool) -> None:
    """
    Start the server.
    """
    # will print an error if not
    check_docker_running()

    info("Starting server...")
    info("Finding Docker daemon.")
    docker_client = docker.from_env()

    # check if name is allowed for docker volume, else exit
    check_config_name_allowed(ctx.name)

    # check that this server is not already running
    running_servers = docker_client.containers.list(
        filters={"label": f"{APPNAME}-type=server"})
    for server in running_servers:
        if server.name == f"{APPNAME}-{ctx.name}-{ctx.scope}-server":
            error(f"Server {Fore.RED}{ctx.name}{Style.RESET_ALL} "
                  "is already running")
            exit(1)

    # Determine image-name. First we check if the option --image has been used.
    # Then we check if the image has been specified in the config file, and
    # finally we use the default settings from the package.
    if image is None:
        custom_images: dict = ctx.config.get('images')
        if custom_images:
            image = custom_images.get('server')
        if not image:
            image = f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_SERVER_IMAGE}"

    info(f"Pulling latest server image '{image}'.")
    try:
        pull_if_newer(docker.from_env(), image)
        # docker_client.images.pull(image)
    except Exception as e:
        warning(' ... Getting latest server image failed:')
        warning(f"     {e}")
    else:
        info(" ... success!")

    info("Creating mounts")
    config_file = "/mnt/config.yaml"
    mounts = [
        docker.types.Mount(
            config_file, str(ctx.config_file), type="bind"
        )
    ]

    if mount_src:
        mount_src = os.path.abspath(mount_src)
        mounts.append(docker.types.Mount("/vantage6", mount_src, type="bind"))
    # FIXME: code duplication with cli_server_import()
    # try to mount database
    uri = ctx.config['uri']
    url = make_url(uri)
    environment_vars = None

    # If host is None, we're dealing with a file-based DB, like SQLite
    if (url.host is None):
        db_path = url.database

        if not os.path.isabs(db_path):
            # We're dealing with a relative path here -> make it absolute
            db_path = ctx.data_dir / url.database

        basename = os.path.basename(db_path)
        dirname = os.path.dirname(db_path)
        os.makedirs(dirname, exist_ok=True)

        # we're mounting the entire folder that contains the database
        mounts.append(docker.types.Mount(
            "/mnt/database/", dirname, type="bind"
        ))

        environment_vars = {
            "VANTAGE6_DB_URI": f"sqlite:////mnt/database/{basename}",
            "VANTAGE6_CONFIG_NAME": ctx.config_file_name
        }

    else:
        warning(f"Database could not be transferred, make sure {url.host} "
                "is reachable from the Docker container")
        info("Consider using the docker-compose method to start a server")

    # Create a docker network for the server and other services like RabbitMQ
    # to reside in
    server_network_mgr = NetworkManager(
        network_name=f"{APPNAME}-{ctx.name}-{ctx.scope}-network"
    )
    server_network_mgr.create_network(is_internal=False)

    if start_rabbitmq or ctx.config.get('rabbitmq') and \
            ctx.config['rabbitmq'].get('start_with_server', False):
        # Note that ctx.data_dir has been created at this point, which is
        # required for putting some RabbitMQ configuration files inside
        info('Starting RabbitMQ container')
        _start_rabbitmq(ctx, rabbitmq_image, server_network_mgr)
    elif ctx.config.get('rabbitmq'):
        info("RabbitMQ is provided in the config file as external service. "
             "Assuming this service is up and running.")
    else:
        warning('Message queue disabled! This means that the vantage6 server '
                'cannot be scaled horizontally!')

    # start the UI if requested
    if start_ui or ctx.config.get('ui') and ctx.config['ui'].get('enabled'):
        _start_ui(docker_client, ctx, ui_port)

    # The `ip` and `port` refer here to the ip and port within the container.
    # So we do not really care that is it listening on all interfaces.
    internal_port = 5000
    cmd = (
        f'uwsgi --http :{internal_port} --gevent 1000 --http-websockets '
        '--master --callable app --disable-logging '
        '--wsgi-file /vantage6/vantage6-server/vantage6/server/wsgi.py '
        f'--pyargv {config_file}'
    )
    info(cmd)

    info("Run Docker container")
    port_ = str(port or ctx.config["port"] or 5000)
    container = docker_client.containers.run(
        image,
        command=cmd,
        mounts=mounts,
        detach=True,
        labels={
            f"{APPNAME}-type": "server",
            "name": ctx.config_file_name
        },
        environment=environment_vars,
        ports={f"{internal_port}/tcp": (ip, port_)},
        name=ctx.docker_container_name,
        auto_remove=not keep,
        tty=True,
        network=server_network_mgr.network_name
    )

    info(f"Success! container id = {container.id}")

    if attach:
        logs = container.attach(stream=True, logs=True, stdout=True)
        Thread(target=print_log_worker, args=(logs,), daemon=True).start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                info("Closing log file. Keyboard Interrupt.")
                info("Note that your server is still running! Shut it down "
                     f"with {Fore.RED}v6 server stop{Style.RESET_ALL}")
                exit(0)


def _start_rabbitmq(ctx: ServerContext, rabbitmq_image: str,
                    network_mgr: NetworkManager) -> None:
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
    rabbit_uri = ctx.config['rabbitmq'].get('uri')
    if not rabbit_uri:
        error("No RabbitMQ URI found in the configuration file! Please add"
              "a 'uri' key to the 'rabbitmq' section of the configuration.")
        exit(1)
    # kick off RabbitMQ container
    rabbit_mgr = RabbitMQManager(
        ctx=ctx, network_mgr=network_mgr, image=rabbitmq_image)
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
    ui_config = ctx.config.get('ui')
    if ui_config and not ui_port:
        ui_port = ui_config.get('port')

    # check if the port is valid
    # TODO make function to check if port is valid, and use in more places
    if not isinstance(ui_port, int) or not 0 < ui_port < 65536:
        warning(f"UI port '{ui_port}' is not valid! Using default port "
                f"{DEFAULT_UI_PORT}")
        ui_port = DEFAULT_UI_PORT

    # find image to use
    custom_images: dict = ctx.config.get('images')
    image = None
    if custom_images:
        image = custom_images.get('ui')
    if not image:
        image = f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_UI_IMAGE}"

    info(f"Pulling latest UI image '{image}'.")
    try:
        pull_if_newer(docker.from_env(), image)
        # docker_client.images.pull(image)
    except Exception as e:
        warning(' ... Getting latest node image failed:')
        warning(f"     {e}")
    else:
        info(" ... success!")

    # set environment variables
    env_vars = {
        "SERVER_URL": f"http://localhost:{ctx.config.get('port')}",
        "API_PATH": ctx.config.get("api_path"),
    }

    # stop the UI container if it is already running
    stop_ui(client, ctx)

    info(f'Starting User Interface at port {ui_port}')
    ui_container_name = f"{APPNAME}-{ctx.name}-{ctx.scope}-ui"
    client.containers.run(
        image,
        detach=True,
        labels={
            f"{APPNAME}-type": "ui",
            "name": ctx.config_file_name
        },
        ports={"80/tcp": (ctx.config.get('ip'), ui_port)},
        name=ui_container_name,
        environment=env_vars,
        tty=True,
    )
