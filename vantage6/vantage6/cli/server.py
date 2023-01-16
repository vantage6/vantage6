import click
import questionary as q
import docker
import os
import time
import subprocess

from typing import Callable, Type, Iterable
from threading import Thread
from functools import wraps
from colorama import (Fore, Style)
from sqlalchemy.engine.url import make_url
from docker.client import DockerClient

from vantage6.common import (info, warning, error, debug as debug_msg,
                             check_config_writeable)
from vantage6.common.docker.addons import (
    pull_if_newer, check_docker_running, remove_container,
    get_server_config_name, get_container, get_num_nonempty_networks,
    get_network, delete_network
)
from vantage6.common.docker.network_manager import NetworkManager
from vantage6.common.globals import (
    APPNAME,
    STRING_ENCODING,
    DEFAULT_DOCKER_REGISTRY,
    DEFAULT_SERVER_IMAGE
)
from vantage6.cli.rabbitmq import split_rabbitmq_uri

from vantage6.cli.globals import (DEFAULT_SERVER_ENVIRONMENT,
                                  DEFAULT_SERVER_SYSTEM_FOLDERS)
from vantage6.cli.context import ServerContext
from vantage6.cli.configuration_wizard import (
    select_configuration_questionaire,
    configuration_wizard
)
from vantage6.cli.utils import check_config_name_allowed
from vantage6.cli.rabbitmq.queue_manager import RabbitMQManager
from vantage6.cli import __version__, rabbitmq


def click_insert_context(func: Callable) -> Callable:
    """
    Supply the Click function with additional context parameters. The context
    is then passed to the function as the first argument.

    Parameters
    ----------
    func : Callable
        function you want the context to be passed to

    Returns
    -------
    Callable
        Click function with context
    """
    @click.option('-n', '--name', default=None,
                  help="name of the configuration you want to use.")
    @click.option('-c', '--config', default=None,
                  help='absolute path to configuration-file; overrides NAME')
    @click.option('-e', '--environment',
                  default=DEFAULT_SERVER_ENVIRONMENT,
                  help='configuration environment to use')
    @click.option('--system', 'system_folders', flag_value=True)
    @click.option('--user', 'system_folders', flag_value=False,
                  default=DEFAULT_SERVER_SYSTEM_FOLDERS)
    @wraps(func)
    def func_with_context(name: str, config: str, environment: str,
                          system_folders: bool, *args, **kwargs) -> Callable:
        """
        Decorator function that adds the context to the function.

        Parameters
        ----------
        name : str
            name of the configuration you want to use.
        config : str
            path to configuration file, overrides name
        environment : str
            DTAP environment to use
        system_folders : bool
            Wether to use system folders or not

        Returns
        -------
        Callable
            Decorated function
        """
        # path to configuration file always overrides name
        if config:
            ctx = ServerContext.from_external_config_file(
                config,
                environment,
                system_folders
            )
            return func(ctx, *args, **kwargs)

        # in case no name is supplied, ask the user to select one
        if not name:
            try:
                # select configuration if none supplied
                name, environment = select_configuration_questionaire(
                    "server", system_folders
                )
            except Exception:
                error("No configurations could be found!")
                exit(1)

        ctx = get_server_context(name, environment, system_folders)
        return func(ctx, *args, **kwargs)

    return func_with_context


@click.group(name='server')
def cli_server() -> None:
    """Subcommand `vserver`."""


#
#   start
#
@cli_server.command(name='start')
@click.option('--ip', default=None, help='ip address to listen on')
@click.option('-p', '--port', default=None, type=int, help='port to listen on')
@click.option('-i', '--image', default=None, help="Server Docker image to use")
@click.option('--rabbitmq-image', default=None,
              help="RabbitMQ docker image to use")
@click.option('--keep/--auto-remove', default=False,
              help="Keep image after finishing")
@click.option('--mount-src', default='',
              help="mount vantage6-master package source")
@click.option('--attach/--detach', default=False,
              help="Attach server logs to the console after start")
@click_insert_context
def cli_server_start(ctx: Type[ServerContext], ip: str, port: int, image: str,
                     rabbitmq_image: str, keep: bool, mount_src: str,
                     attach: bool) -> None:
    """
    Start the server in a Docker container.

    Parameters
    ----------
    ctx : Type[ServerContext]
        Server context object
    ip : str
        ip interface to listen on
    port : int
        port to listen on
    image : str
        Server Docker image to use
    rabbitmq_image : str
        RabbitMQ docker image to use
    keep : bool
        Wether to keep the image after the server has finished, useful for
        debugging
    mount_src : str
        Path to the vantage6 package source, this overrides the source code in
        the container. This is useful when developing and testing the server.
    attach : bool
        Wether to attach the server logs to the console after starting the
        server.
    """
    info("Starting server...")
    info("Finding Docker daemon.")
    docker_client = docker.from_env()
    # will print an error if not
    check_docker_running()

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
        image = ctx.config.get(
            "image",
            f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_SERVER_IMAGE}"
        )
    info(f"Pulling latest server image '{image}'.")
    try:
        pull_if_newer(docker.from_env(), image)
        # docker_client.images.pull(image)
    except Exception as e:
        warning(' ... Getting latest node image failed:')
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

    # Note that ctx.data_dir has been created at this point, which is required
    # for putting some RabbitMQ configuration files inside
    info('Starting RabbitMQ container')
    _start_rabbitmq(ctx, rabbitmq_image, server_network_mgr)

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
                     f"with {Fore.RED}vserver stop{Style.RESET_ALL}")
                exit(0)


#
#   list
#
@cli_server.command(name='list')
def cli_server_configuration_list() -> None:
    """
    Print the available configurations.
    """
    client = docker.from_env()
    check_docker_running()

    running_server = client.containers.list(
        filters={"label": f"{APPNAME}-type=server"})
    running_node_names = []
    for node in running_server:
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
    configs, f1 = ServerContext.available_configurations(
        system_folders=True)
    for config in configs:
        status = running if f"{APPNAME}-{config.name}-system-server" in \
            running_node_names else stopped
        click.echo(
            f"{config.name:25}"
            f"{str(config.available_environments):32}"
            f"{status:25} System "
        )

    # user folders
    configs, f2 = ServerContext.available_configurations(
        system_folders=False)
    for config in configs:
        status = running if f"{APPNAME}-{config.name}-user-server" in \
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
#   files
#
@cli_server.command(name='files')
@click_insert_context
def cli_server_files(ctx: Type[ServerContext]) -> None:
    """
    List files locations of a server instance.

    Parameters
    ----------
    ctx : Type[ServerContext]
        Server context object
    """
    info(f"Configuration file = {ctx.config_file}")
    info(f"Log file           = {ctx.log_file}")
    info(f"Database           = {ctx.get_database_uri()}")


#
#   new
#
@cli_server.command(name='new')
@click.option('-n', '--name', default=None,
              help="name of the configuration you want to use.")
@click.option('-e', '--environment', default=DEFAULT_SERVER_ENVIRONMENT,
              help='configuration environment to use')
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=DEFAULT_SERVER_SYSTEM_FOLDERS)
def cli_server_new(name: str, environment: str, system_folders: bool) -> None:
    """
    Create a new server configuration.

    Parameters
    ----------
    name : str
        name of the new configuration
    environment : str
        DTAP environment you want to configure
    system_folders : bool
        Wether to use system folders or not
    """
    if not name:
        name = q.text("Please enter a configuration-name:").ask()
        if name.count(" ") > 0:
            name = name.replace(" ", "-")
            info(f"Replaced spaces from configuration name: {name}")

    # check if name is allowed for docker volume, else exit
    check_config_name_allowed(name)

    # check that this config does not exist
    try:
        if ServerContext.config_exists(name, environment, system_folders):
            error(
                f"Configuration {Fore.RED}{name}{Style.RESET_ALL} with "
                f"environment {Fore.RED}{environment}{Style.RESET_ALL} "
                f"already exists!"
            )
            exit(1)
    except Exception as e:
        error(e)
        exit(1)

    # Check that we can write in this folder
    if not check_config_writeable(system_folders):
        error("Your user does not have write access to all folders. Exiting")
        info(f"Create a new server using '{Fore.GREEN}vserver new "
             "--user{Style.RESET_ALL}' instead!")
        exit(1)

    # create config in ctx location
    cfg_file = configuration_wizard("server", name, environment=environment,
                                    system_folders=system_folders)
    info(f"New configuration created: {Fore.GREEN}{cfg_file}{Style.RESET_ALL}")

    # info(f"root user created.")
    flag = "" if system_folders else "--user"
    info(f"You can start the server by running {Fore.GREEN}vserver start "
         f"{flag}{Style.RESET_ALL}")


#
#   import
#
# TODO this method has a lot of duplicated code from `start`
@cli_server.command(name='import')
@click.argument('file_', type=click.Path(exists=True))
@click.option('--drop-all', is_flag=True, default=False)
@click.option('-i', '--image', default=None, help="Node Docker image to use")
@click.option('--mount-src', default='',
              help="mount vantage6-master package source")
@click.option('--keep/--auto-remove', default=False,
              help="Keep image after finishing")
@click_insert_context
def cli_server_import(ctx: Type[ServerContext], file_: str, drop_all: bool,
                      image: str, mount_src: str, keep: bool) -> None:
    """
    Batch import organizations/collaborations/users and tasks.

    Parameters
    ----------
    ctx : Type[ServerContext]
        Server context object
    file_ : str
        Yaml file containing the vantage6 formatted data to import
    drop_all : bool
        Wether to drop all data before importing
    image : str
        Node Docker image to use which contains the import script
    mount_src : str
        Vantage6 source location, this will overwrite the source code in the
        container. Useful for debugging/development.
    keep : bool
        Wether to keep the image after finishing/crashing. Useful for
        debugging.
    """
    info("Starting server...")
    info("Finding Docker daemon.")
    docker_client = docker.from_env()
    # will print an error if not
    check_docker_running()

    # check if name is allowed for docker volume, else exit
    check_config_name_allowed(ctx.name)

    # pull latest Docker image
    if image is None:
        image = ctx.config.get(
            "image",
            f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_SERVER_IMAGE}"
        )
    info(f"Pulling latest server image '{image}'.")
    try:
        docker_client.images.pull(image)
    except Exception as e:
        warning(' ... Getting latest node image failed:')
        warning(f"     {e}")
    else:
        info(" ... success!")

    info("Creating mounts")
    mounts = [
        docker.types.Mount(
            "/mnt/config.yaml", str(ctx.config_file), type="bind"
        ),
        docker.types.Mount(
            "/mnt/import.yaml", str(file_), type="bind"
        )
    ]

    # FIXME: code duplication with cli_server_start()
    # try to mount database
    uri = ctx.config['uri']
    url = make_url(uri)
    environment_vars = None

    if mount_src:
        mount_src = os.path.abspath(mount_src)
        mounts.append(docker.types.Mount("/vantage6", mount_src, type="bind"))

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
            "VANTAGE6_DB_URI": f"sqlite:////mnt/database/{basename}"
        }

    else:
        warning(f"Database could not be transferred, make sure {url.host} "
                "is reachable from the Docker container")
        info("Consider using the docker-compose method to start a server")

    drop_all_ = "--drop-all" if drop_all else ""
    cmd = f'vserver-local import -c /mnt/config.yaml -e {ctx.environment} ' \
          f'{drop_all_} /mnt/import.yaml'

    info(cmd)

    info("Run Docker container")
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
        auto_remove=not keep,
        tty=True
    )
    logs = container.logs(stream=True, stdout=True)
    Thread(target=print_log_worker, args=(logs,), daemon=False).start()

    info(f"Success! container id = {container.id}")


#
#   shell
#
@cli_server.command(name='shell')
@click_insert_context
def cli_server_shell(ctx: Type[ServerContext]) -> None:
    """
    Run an iPython shell in the server container and attach the ORM. This
    can be used to modify the database.

    Parameters
    ----------
    ctx : Type[ServerContext]
        Server context object
    """
    docker_client = docker.from_env()
    # will print an error if not
    check_docker_running()

    running_servers = docker_client.containers.list(
        filters={"label": f"{APPNAME}-type=server"})

    if ctx.docker_container_name not in [s.name for s in running_servers]:
        error(f"Server {Fore.RED}{ctx.name}{Style.RESET_ALL} is not running?")
        return

    try:
        subprocess.run(['docker', 'exec', '-it', ctx.docker_container_name,
                        'vserver-local', 'shell', '-c', '/mnt/config.yaml'])
    except Exception as e:
        info("Failed to start subprocess...")
        debug_msg(e)


#
#   stop
#
@cli_server.command(name='stop')
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option('-e', '--environment', default=DEFAULT_SERVER_ENVIRONMENT,
              help='configuration environment to use')
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=DEFAULT_SERVER_SYSTEM_FOLDERS)
@click.option('--all', 'all_servers', flag_value=True, help="Stop all servers")
def cli_server_stop(name: str, environment: str, system_folders: bool,
                    all_servers: bool):
    """
    Stop one or all running server(s).

    Parameters
    ----------
    name : str
        Name of the server to stop
    environment : str
        DTAP environment to use
    system_folders : bool
        Wether to use system folders or not
    all_servers : bool
        Wether to stop all servers or not
    """
    client = docker.from_env()
    check_docker_running()

    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type=server"})

    if not running_servers:
        warning("No servers are currently running.")
        return

    running_server_names = [server.name for server in running_servers]

    if all_servers:
        for container_name in running_server_names:
            _stop_server_containers(client, container_name, environment,
                                    system_folders)
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

    _stop_server_containers(client, container_name, environment,
                            system_folders)


#
#   attach
#
@cli_server.command(name='attach')
@click.option("-n", "--name", default=None, help="configuration name")
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=DEFAULT_SERVER_SYSTEM_FOLDERS)
def cli_server_attach(name: str, system_folders: bool) -> None:
    """
    Attach the logs from the docker container to the terminal.

    Parameters
    ----------
    name : str
        Configuration name
    system_folders : bool
        Wether to use system folders or not
    """
    client = docker.from_env()
    check_docker_running()

    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type=server"})
    running_server_names = [node.name for node in running_servers]

    if not name:
        name = q.select("Select the server you wish to inspect:",
                        choices=running_server_names).ask()
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}-server"

    if name in running_server_names:
        container = client.containers.get(name)
        logs = container.attach(stream=True, logs=True, stdout=True)
        Thread(target=print_log_worker, args=(logs,), daemon=True).start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                info("Closing log file. Keyboard Interrupt.")
                info("Note that your server is still running! Shut it down "
                     f"with {Fore.RED}vserver stop{Style.RESET_ALL}")
                exit(0)
    else:
        error(f"{Fore.RED}{name}{Style.RESET_ALL} was not running!?")


#
#   version
#
@cli_server.command(name='version')
@click.option("-n", "--name", default=None, help="configuration name")
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=DEFAULT_SERVER_SYSTEM_FOLDERS)
def cli_server_version(name: str, system_folders: bool):
    """
    Print the version of the vantage6 services.

    Parameters
    ----------
    name : str
        Name of the server to inspect
    system_folders : bool
        Wether to use system folders or not
    """
    client = docker.from_env()
    check_docker_running()

    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type=server"})
    running_server_names = [server.name for server in running_servers]

    if not name:
        if not running_server_names:
            error("No servers are running! You can only check the version for "
                  "servers that are running")
            exit(1)
        name = q.select("Select the server you wish to inspect:",
                        choices=running_server_names).ask()
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}"

    if name in running_server_names:
        container = client.containers.get(name)
        version = container.exec_run(cmd='vserver-local version',
                                     stdout=True)
        click.echo({"server": version.output.decode('utf-8'),
                    "cli": __version__})
    else:
        error(f"Server {name} is not running! Cannot provide version...")


#
# helper functions
#
def get_server_context(name: str, environment: str, system_folders: bool) \
        -> ServerContext:
    """
    Load the server context from the configuration file.

    Returns
    -------
    ServerContext
        Server context object
    """
    if not ServerContext.config_exists(name, environment, system_folders):
        scope = "system" if system_folders else "user"
        error(
                f"Configuration {Fore.RED}{name}{Style.RESET_ALL} with "
                f"{Fore.RED}{environment}{Style.RESET_ALL} does not exist "
                f"in the {Fore.RED}{scope}{Style.RESET_ALL} folders!"
            )
        exit(1)

    # We do not want to log this here, we do this in the container and not on
    # the host. We only want CLI logging here.
    ServerContext.LOGGING_ENABLED = False

    # create server context, and initialize db
    ctx = ServerContext(name, environment=environment,
                        system_folders=system_folders)

    return ctx


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
    rabbit_uri = ctx.config.get('rabbitmq_uri')
    if not rabbit_uri:
        warning('Message queue disabled! This means that the server '
                'application cannot scale horizontally!')
    elif rabbitmq.is_local_address(rabbit_uri):
        # kick off RabbitMQ container
        rabbit_mgr = RabbitMQManager(
            ctx=ctx, network_mgr=network_mgr, image=rabbitmq_image)
        rabbit_mgr.start()
    else:
        info("Detected that the RabbitMQ service is a external service. "
             "Assuming this service is up and running.")


def _stop_server_containers(client: DockerClient, container_name: str,
                            environment: str, system_folders: bool) -> None:
    """
    Given a server's name, kill its docker container and related (RabbitMQ)
    containers.

    Parameters
    ----------
    client : DockerClient
        Docker client
    container_name : str
        Name of the server to stop
    environment : str
        DTAP environment to use
    system_folders : bool
        Wether to use system folders or not
    """
    # kill the server
    container = client.containers.get(container_name)
    container.kill()
    info(f"Stopped the {Fore.GREEN}{container_name}{Style.RESET_ALL} server.")

    # find the configuration name from the docker container name
    # server name is formatted as f"{APPNAME}-{self.name}-{self.scope}-server"
    scope = "system" if system_folders else "user"
    config_name = get_server_config_name(container_name, scope)

    ctx = get_server_context(config_name, environment, system_folders)

    # delete the server network
    network_name = f"{APPNAME}-{ctx.name}-{ctx.scope}-network"
    network = get_network(client, name=network_name)
    delete_network(network, kill_containers=False)

    # kill RabbitMQ if it exists and no other servers are using to it (i.e. it
    # is not in other docker networks with other containers)
    rabbit_uri = ctx.config.get('rabbitmq_uri')
    if rabbit_uri:
        rabbit_container_name = split_rabbitmq_uri(
            rabbit_uri=rabbit_uri)['host']
        rabbit_container = get_container(client, name=rabbit_container_name)
        if rabbit_container and \
                get_num_nonempty_networks(rabbit_container) == 0:
            remove_container(rabbit_container, kill=True)
            info(f"Stopped the {Fore.GREEN}{rabbit_container_name}"
                 f"{Style.RESET_ALL} container.")


def print_log_worker(logs_stream: Iterable[bytes]) -> None:
    """
    Print the logs from the docker container to the terminal.

    Parameters
    ----------
    logs_stream : Iterable[bytes]
        Output of the `container.attach(.)` method
    """
    for log in logs_stream:
        print(log.decode(STRING_ENCODING), end="")
