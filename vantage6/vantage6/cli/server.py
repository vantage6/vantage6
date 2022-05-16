import click
import questionary as q
import docker
import os
import time
import subprocess
from docker.client import DockerClient

from threading import Thread
from functools import wraps
from colorama import (Fore, Style)
from sqlalchemy.engine.url import make_url

from vantage6.common import (info, warning, error, debug as debug_msg,
                             check_config_write_permissions)
from vantage6.common.docker_addons import (
    pull_if_newer, remove_container_if_exists,
    get_server_config_name
)
from vantage6.common.network_manager import NetworkManager
from vantage6.common.globals import (
    APPNAME,
    STRING_ENCODING,
    DEFAULT_DOCKER_REGISTRY,
    DEFAULT_SERVER_IMAGE
)

# from vantage6.cli import fixture
from vantage6.cli.globals import (DEFAULT_SERVER_ENVIRONMENT,
                                  DEFAULT_SERVER_SYSTEM_FOLDERS)
from vantage6.cli.context import ServerContext
from vantage6.cli.configuration_wizard import (
    select_configuration_questionaire,
    configuration_wizard
)
from vantage6.cli.rabbitmq.queue_manager import RabbitMQManager
from vantage6.cli import __version__


def click_insert_context(func):

    # add option decorators
    @click.option('-n', '--name', default=None,
                  help="name of the configutation you want to use.")
    @click.option('-c', '--config', default=None,
                  help='absolute path to configuration-file; overrides NAME')
    @click.option('-e', '--environment',
                  default=DEFAULT_SERVER_ENVIRONMENT,
                  help='configuration environment to use')
    @click.option('--system', 'system_folders', flag_value=True)
    @click.option('--user', 'system_folders', flag_value=False,
                  default=DEFAULT_SERVER_SYSTEM_FOLDERS)
    @wraps(func)
    def func_with_context(name, config, environment, system_folders,
                          *args, **kwargs):

        # select configuration if none supplied
        if config:
            ctx = ServerContext.from_external_config_file(
                config,
                environment,
                system_folders
            )
        else:
            if name:
                name, environment = (name, environment)
            else:
                try:
                    name, environment = select_configuration_questionaire(
                        "server", system_folders
                    )
                except Exception:
                    error("No configurations could be found!")
                    exit(1)

            # raise error if config could not be found
            if not ServerContext.config_exists(
                name,
                environment,
                system_folders
            ):
                scope = "system" if system_folders else "user"
                error(
                    f"Configuration {Fore.RED}{name}{Style.RESET_ALL} with "
                    f"{Fore.RED}{environment}{Style.RESET_ALL} does not exist "
                    f"in the {Fore.RED}{scope}{Style.RESET_ALL} folders!"
                )
                exit(1)

            # create server context, and initialize db
            ServerContext.LOGGING_ENABLED = False
            ctx = ServerContext(
                name,
                environment=environment,
                system_folders=system_folders
            )

        return func(ctx, *args, **kwargs)
    return func_with_context


@click.group(name='server')
def cli_server():
    """Subcommand `vserver`."""
    pass

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
def cli_server_start(ctx, ip, port, image, rabbitmq_image, keep, mount_src,
                     attach):
    """Start the server."""

    info("Starting server...")
    info("Finding Docker daemon.")
    docker_client = docker.from_env()
    # will print an error if not
    check_if_docker_deamon_is_running(docker_client)

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
    except Exception:
        warning("... alas, no dice!")
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
    environment_vars = {"VANTAGE6_CONFIG_NAME": ctx.config_file_name}

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

        environment_vars["VANTAGE6_DB_URI"] = \
            f"sqlite:////mnt/database/{basename}"
    else:
        warning(f"Database could not be transfered, make sure {url.host} "
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

    info(f"Success! container id = {container}")

    if attach:
        logs = container.attach(stream=True, logs=True, stdout=True)
        Thread(target=print_log_worker, args=(logs,), daemon=True).start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                info("Closing log file. Keyboard Interrupt.")
                exit(0)


def _start_rabbitmq(ctx: ServerContext, rabbitmq_image: str,
                    network_mgr: NetworkManager) -> None:
    """ Starts a RabbitMQ container """
    if not ctx.config.get('rabbitmq'):
        warning('Message queue disabled! This means that the server '
                'application cannot scale horizontally!')
    else:
        # kick off RabbitMQ container
        rabbit_mgr = RabbitMQManager(
            ctx=ctx, network_mgr=network_mgr, image=rabbitmq_image)
        rabbit_mgr.start()


#
#   list
#
@cli_server.command(name='list')
def cli_server_configuration_list():
    """Print the available configurations."""

    client = docker.from_env()
    check_if_docker_deamon_is_running(client)

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
def cli_server_files(ctx):
    """List files locations of a server instance."""
    info(f"Configuration file = {ctx.config_file}")
    info(f"Log file           = {ctx.log_file}")
    info(f"Database           = {ctx.get_database_uri()}")

#
#   new
#
@cli_server.command(name='new')
@click.option('-n', '--name', default=None,
              help="name of the configutation you want to use.")
@click.option('-e', '--environment', default=DEFAULT_SERVER_ENVIRONMENT,
              help='configuration environment to use')
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=DEFAULT_SERVER_SYSTEM_FOLDERS)
def cli_server_new(name, environment, system_folders):
    """Create new configuration."""

    if not name:
        name = q.text("Please enter a configuration-name:").ask()
        name_new = name.replace(" ", "-")
        if name != name_new:
            info(f"Replaced spaces from configuration name: {name}")
            name = name_new

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
        print(e)
        exit(1)

     # Check that we can write in this folder
    if not check_config_write_permissions(system_folders):
        error("Your user does not have write access to all folders. Exiting")
        info(f"Create a new server using '{Fore.GREEN}vserver new "
             "--user{Style.RESET_ALL}' instead!")
        exit(1)

    # create config in ctx location
    cfg_file = configuration_wizard(
        "server",
        name,
        environment=environment,
        system_folders=system_folders
    )
    info(f"New configuration created: {Fore.GREEN}{cfg_file}{Style.RESET_ALL}")

    # info(f"root user created.")
    flag = "" if system_folders else "--user"
    info(
        f"You can start the server by running "
        f"{Fore.GREEN}vserver start {flag}{Style.RESET_ALL}"
    )

#
#   import
#
# TODO this method has a lot of duplicated code from `start`
@cli_server.command(name='import')
@click.argument('file_', type=click.Path(exists=True))
@click.option('--drop-all', is_flag=True, default=False)
@click.option('-i', '--image', default=None, help="Node Docker image to use")
@click.option('--keep/--auto-remove', default=False,
              help="Keep image after finishing")
@click_insert_context
def cli_server_import(ctx, file_, drop_all, image, keep):
    """ Import organizations/collaborations/users and tasks.

        Especially usefull for testing purposes.
    """
    info("Starting server...")
    info("Finding Docker daemon.")
    docker_client = docker.from_env()
    # will print an error if not
    check_if_docker_deamon_is_running(docker_client)

    # pull lastest Docker image
    if image is None:
        image = ctx.config.get(
            "image",
            f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_SERVER_IMAGE}"
        )
    info(f"Pulling latest server image '{image}'.")
    try:
        docker_client.images.pull(image)
    except Exception:
        warning("... alas, no dice!")
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
        warning(f"Database could not be transfered, make sure {url.host} "
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

    # print_log_worker(container.logs(stream=True))
    # for log in container.logs(stream=True):
    #     print(log.decode("utf-8"))
    # info(f"Check logs files using {Fore.GREEN}docker logs {container.id}"
    #      f"{Style.RESET_ALL}")

    # info("Reading yaml file.")
    # with open(file_) as f:
    #     entities = yaml.safe_load(f.read())

    # info("Adding entities to database.")
    # fixture.load(entities, drop_all=drop_all)


#
#   shell
#
@cli_server.command(name='shell')
@click_insert_context
def cli_server_shell(ctx):
    """ Run a iPython shell. """

    docker_client = docker.from_env()
    # will print an error if not
    check_if_docker_deamon_is_running(docker_client)

    running_servers = docker_client.containers.list(
        filters={"label": f"{APPNAME}-type=server"})

    if not ctx.docker_container_name in [s.name for s in running_servers]:
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
@click.option("-n", "--name", default=None, help="configuration name")
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=DEFAULT_SERVER_SYSTEM_FOLDERS)
@click.option('--all', 'all_servers', flag_value=True)
def cli_server_stop(name, system_folders, all_servers):
    """Stop a or all running server. """

    client = docker.from_env()
    check_if_docker_deamon_is_running(client)

    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type=server"})

    if not running_servers:
        warning("No servers are currently running.")
        return

    running_server_names = [server.name for server in running_servers]

    if all_servers:
        for container_name in running_server_names:
            _stop_server_containers(client, container_name, system_folders)
    else:
        if not name:
            container_name = q.select("Select the server you wish to stop:",
                                      choices=running_server_names).ask()
        else:

            post_fix = "system" if system_folders else "user"
            container_name = f"{APPNAME}-{name}-{post_fix}-server"

        if container_name in running_server_names:
            _stop_server_containers(client, container_name, system_folders)
        else:
            error(f"{Fore.RED}{name}{Style.RESET_ALL} is not running?")


def _stop_server_containers(client: DockerClient, container_name: str,
                            system_folders: bool) -> None:
    """
    Given a server's name, kill its docker container and related (RabbitMQ)
    containers.
    """
    # kill the server
    container = client.containers.get(container_name)
    container.kill()
    info(f"Stopped the {Fore.GREEN}{container_name}{Style.RESET_ALL} server.")

    # find the configuration name from the docker container name
    # server name is formatted as f"{APPNAME}-{self.name}-{self.scope}-server"
    scope = "system" if system_folders else "user"
    config_name = get_server_config_name(container_name, scope)

    # kill the RabbitMQ container (if it exists)
    rabbit_container_name = f'{APPNAME}-{config_name}-rabbitmq'
    remove_container_if_exists(client, name=rabbit_container_name)
    info(f"Stopped the {Fore.GREEN}{rabbit_container_name}{Style.RESET_ALL} "
         "container.")


#
#   attach
#
@cli_server.command(name='attach')
@click.option("-n", "--name", default=None, help="configuration name")
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False,
              default=DEFAULT_SERVER_SYSTEM_FOLDERS)
def cli_server_attach(name, system_folders):
    """Attach the logs from the docker container to the terminal."""

    client = docker.from_env()
    check_if_docker_deamon_is_running(client)

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
                exit(0)
    else:
        error(f"{Fore.RED}{name}{Style.RESET_ALL} was not running!?")


def check_if_docker_deamon_is_running(docker_client):
    try:
        docker_client.ping()
    except Exception:
        error("Docker socket can not be found. Make sure Docker is running.")
        exit()


#
#   version
#
@cli_server.command(name='version')
@click.option("-n", "--name", default=None, help="configuration name")
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False, default=
              DEFAULT_SERVER_SYSTEM_FOLDERS)
def cli_server_version(name, system_folders):
    """Returns current version of vantage6 services installed."""

    client = docker.from_env()
    check_if_docker_deamon_is_running(client)

    running_servers = client.containers.list(
        filters={"label": f"{APPNAME}-type=node"})
    running_server_names = [node.name for node in running_servers]

    if not name:
        name = q.select("Select the server you wish to inspect:",
                        choices=running_server_names).ask()
    else:
        post_fix = "system" if system_folders else "user"
        name = f"{APPNAME}-{name}-{post_fix}"

    if name in running_server_names:
        container = client.containers.get(name)
        version = container.exec_run(cmd='vserver-local version', stdout = True)
        click.echo({"server": version.output.decode('utf-8'), "cli":__version__})

def print_log_worker(logs_stream):
    for log in logs_stream:
        print(log.decode(STRING_ENCODING), end="")
