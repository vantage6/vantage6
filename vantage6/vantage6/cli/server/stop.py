import itertools

import click
import questionary as q
import docker
from colorama import (Fore, Style)
from docker.client import DockerClient

from vantage6.common import info, warning, error
from vantage6.common.docker.addons import (
    check_docker_running, remove_container,
    get_server_config_name, get_container, get_num_nonempty_networks,
    get_network, delete_network, remove_container_if_exists
)
from vantage6.common.globals import APPNAME
from vantage6.cli.rabbitmq import split_rabbitmq_uri

from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS
from vantage6.cli.context import ServerContext
from vantage6.cli.utils import remove_file
from vantage6.cli.server.common import get_server_context, stop_ui


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=DEFAULT_SERVER_SYSTEM_FOLDERS)
@click.option('--all', 'all_servers', flag_value=True, help="Stop all servers")
def cli_server_stop(name: str, system_folders: bool, all_servers: bool):
    """
    Stop one or all running server(s).
    """
    check_docker_running()
    client = docker.from_env()

    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type=server"})

    if not running_servers:
        warning("No servers are currently running.")
        return

    running_server_names = [server.name for server in running_servers]

    if all_servers:
        for container_name in running_server_names:
            _stop_server_containers(client, container_name, system_folders)
        return

    # make sure we have a configuration name to work with
    if not name:
        container_name = q.select("Select the server you wish to stop:",
                                  choices=running_server_names).ask()
    else:
        post_fix = "system" if system_folders else "user"
        container_name = f"{APPNAME}-{name}-{post_fix}-server"

    if container_name not in running_server_names:
        error(f"{Fore.RED}{name}{Style.RESET_ALL} is not running!")
        return

    _stop_server_containers(client, container_name, system_folders)


def _stop_server_containers(client: DockerClient, container_name: str,
                            system_folders: bool) -> None:
    """
    Given a server's name, kill its docker container and related (RabbitMQ)
    containers.

    Parameters
    ----------
    client : DockerClient
        Docker client
    container_name : str
        Name of the server to stop
    system_folders : bool
        Wether to use system folders or not
    """
    # kill the server
    remove_container_if_exists(client, name=container_name)
    info(f"Stopped the {Fore.GREEN}{container_name}{Style.RESET_ALL} server.")

    # find the configuration name from the docker container name
    # server name is formatted as f"{APPNAME}-{self.name}-{self.scope}-server"
    scope = "system" if system_folders else "user"
    config_name = get_server_config_name(container_name, scope)

    ctx = get_server_context(config_name, system_folders)

    # kill the UI container (if it exists)
    stop_ui(client, ctx)

    # delete the server network
    network_name = f"{APPNAME}-{ctx.name}-{ctx.scope}-network"
    network = get_network(client, name=network_name)
    delete_network(network, kill_containers=False)

    # kill RabbitMQ if it exists and no other servers are using to it (i.e. it
    # is not in other docker networks with other containers)
    rabbit_uri = ctx.config.get('rabbitmq', {}).get('uri')
    if rabbit_uri:
        rabbit_container_name = split_rabbitmq_uri(
            rabbit_uri=rabbit_uri)['host']
        rabbit_container = get_container(client, name=rabbit_container_name)
        if rabbit_container and \
                get_num_nonempty_networks(rabbit_container) == 0:
            remove_container(rabbit_container, kill=True)
            info(f"Stopped the {Fore.GREEN}{rabbit_container_name}"
                 f"{Style.RESET_ALL} container.")


# TODO this should be refactored into its own module and get a click command
# attached
@click.pass_context
def vserver_remove(
    click_ctx: click.Context, ctx: ServerContext, name: str,
    system_folders: bool, force: bool
) -> None:
    """
    Function to remove a server.

    Parameters
    ----------
    ctx : ServerContext
        Server context object
    name : str
        Name of the server to remove
    system_folders : bool
        Whether to use system folders or not
    force : bool
        Whether to ask for confirmation before removing or not
    """
    check_docker_running()

    # first stop server
    click_ctx.invoke(
        cli_server_stop, name=name, system_folders=system_folders,
        all_servers=False
    )

    if not force:
        if not q.confirm(
            "This server will be deleted permanently including its "
            "configuration. Are you sure?", default=False
        ).ask():
            info("Server will not be deleted")
            exit(0)

    # now remove the folders...
    info(f"Removing configuration file {ctx.config_file}")
    remove_file(ctx.config_file, 'configuration')

    info(f"Removing log file {ctx.log_file}")
    for handler in itertools.chain(ctx.log.handlers, ctx.log.root.handlers):
        handler.close()
    remove_file(ctx.log_file, 'log')
