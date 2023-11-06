import os
from threading import Thread
import time

import click
import docker
from colorama import (Fore, Style)
from sqlalchemy.engine.url import make_url

from vantage6.common import info, warning, error
from vantage6.common.docker.addons import (
    pull_if_newer, check_docker_running
)
from vantage6.common.globals import (
    APPNAME,
    DEFAULT_DOCKER_REGISTRY,
    DEFAULT_ALGO_STORE_IMAGE,
    InstanceType
)

from vantage6.cli.globals import AlgoStoreGlobals
from vantage6.cli.context.server import ServerContext
from vantage6.cli.utils import check_config_name_allowed
from vantage6.cli.server.common import print_log_worker
from vantage6.cli.common.decorator import insert_context


@click.command()
@click.option('--ip', default=None, help='IP address to listen on')
@click.option('-p', '--port', default=None, type=int, help='Port to listen on')
@click.option('-i', '--image', default=None,
              help="Algorithm store Docker image to use")
@click.option('--keep/--auto-remove', default=False,
              help="Keep image after algorithm store has been stopped. Useful "
              "for debugging")
@click.option('--mount-src', default='',
              help="Override vantage6 source code in container with the source"
              " code in this path")
@click.option('--attach/--detach', default=False,
              help="Print server logs to the console after start")
@insert_context(InstanceType.ALGORITHM_STORE)
def cli_algo_store_start(
    ctx: ServerContext, ip: str, port: int, image: str, keep: bool,
    mount_src: str, attach: bool
) -> None:
    """
    Start the algorithm store server.
    """
    # will print an error if not
    check_docker_running()

    info("Starting algorithm store...")
    info("Finding Docker daemon.")
    docker_client = docker.from_env()

    # check if name is allowed for docker volume, else exit
    check_config_name_allowed(ctx.name)

    # check that this server is not already running
    running_servers = docker_client.containers.list(
        filters={"label": f"{APPNAME}-type={InstanceType.ALGORITHM_STORE}"})
    for server in running_servers:
        if server.name == (f"{APPNAME}-{ctx.name}-{ctx.scope}-"
                           f"{InstanceType.ALGORITHM_STORE}"):
            error(f"Server {Fore.RED}{ctx.name}{Style.RESET_ALL} "
                  "is already running")
            exit(1)

    # Determine image-name. First we check if the option --image has been used.
    # Then we check if the image has been specified in the config file, and
    # finally we use the default settings from the package.
    if image is None:
        custom_images: dict = ctx.config.get('images')
        if custom_images:
            image = custom_images.get('algorithm-store')
        if not image:
            image = f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_ALGO_STORE_IMAGE}"

    info(f"Pulling latest image '{image}'.")
    try:
        pull_if_newer(docker.from_env(), image)
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
            AlgoStoreGlobals.DB_URI_ENV_VAR:
                f"sqlite:////mnt/database/{basename}",
            AlgoStoreGlobals.CONFIG_NAME_ENV_VAR: ctx.config_file_name
        }

    else:
        warning(f"Database could not be transferred, make sure {url.host} "
                "is reachable from the Docker container")
        info("Consider using the docker-compose method to start a server")

    # The `ip` and `port` refer here to the ip and port within the container.
    # So we do not really care that is it listening on all interfaces.
    internal_port = 5000
    cmd = (
        f'uwsgi --http :{internal_port} --gevent 1000 --http-websockets '
        '--master --callable app --disable-logging '
        '--wsgi-file /vantage6/vantage6-algorithm-store/vantage6/algorithm'
        f'/store/wsgi.py --pyargv {config_file}'
    )
    info(cmd)

    info("Run Docker container")
    port_ = str(port or ctx.config["port"] or AlgoStoreGlobals.PORT)
    container = docker_client.containers.run(
        image,
        command=cmd,
        mounts=mounts,
        detach=True,
        labels={
            f"{APPNAME}-type": InstanceType.SERVER,
            "name": ctx.config_file_name
        },
        environment=environment_vars,
        ports={f"{internal_port}/tcp": (ip, port_)},
        name=ctx.docker_container_name,
        auto_remove=not keep,
        tty=True,
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
                     f"with {Fore.RED}v6 algorithm-store stop{Style.RESET_ALL}"
                     )
                exit(0)
