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
def cli_algo_store_start(
    ctx: ServerContext, ip: str, port: int, image: str, start_ui: bool,
    ui_port: int, start_rabbitmq: bool,
    rabbitmq_image: str, keep: bool, mount_src: str,
    attach: bool
) -> None:
    """
    Start the algorithm store server.
    """
    pass

