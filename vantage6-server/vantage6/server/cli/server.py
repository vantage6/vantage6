import click
import questionary as q
import IPython
import yaml

from functools import wraps
from traitlets.config import get_config
from colorama import Fore, Style

from vantage6.common import (
    info,
    warning,
    error,
    check_config_writeable
)
from vantage6.server.model.base import Database
from vantage6.server import ServerApp, run_dev_server
from vantage6.cli.globals import (
    DEFAULT_SERVER_ENVIRONMENT as S_ENV,
    DEFAULT_SERVER_SYSTEM_FOLDERS as S_FOL
)
from vantage6.server.controller import fixture
from vantage6.cli.configuration_wizard import (
    configuration_wizard,
    select_configuration_questionaire
)
from vantage6.cli.context import ServerContext
from vantage6.server._version import __version__


help_ = {
    "name": "name of the configutation you want to use.",
    "config": "absolute path to configuration-file; overrides NAME",
    "env": "configuration environment to use"
}


def click_insert_context(func: callable) -> callable:
    """
    Decorator to insert a ServerContext object into the function.

    This decorator will insert a ServerContext object into the function. The
    ServerContext object is created based on the configuration file that is
    selected by the user. The user can select the configuration file by
    supplying the name of the configuration file, or by supplying the path to
    the configuration file. The decorator will also initialize the database
    connection.

    Parameters
    ----------
    func : callable
        The function to decorate.

    Returns
    -------
    callable
        The decorated function.
    """

    # add option decorators
    @click.option('-n', '--name', default=None, help=help_["name"])
    @click.option('-c', '--config', default=None, help=help_["config"])
    @click.option('-e', '--environment', default=S_ENV, help=help_["env"])
    @click.option('--system', 'system_folders', flag_value=True)
    @click.option('--user', 'system_folders', flag_value=False, default=S_FOL)
    @wraps(func)
    def func_with_context(name: str, config: str, environment: str,
                          system_folders: bool, *args, **kwargs) -> callable:

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
                    exit()

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
            ctx = ServerContext(
                name,
                environment=environment,
                system_folders=system_folders
            )

        # initialize database (singleton)
        allow_drop_all = ctx.config["allow_drop_all"]
        Database().connect(uri=ctx.get_database_uri(),
                           allow_drop_all=allow_drop_all)

        return func(ctx, *args, **kwargs)

    return func_with_context


@click.group(name='server')
def cli_server() -> None:
    """Subcommand `vserver`."""
    pass


#
#   start
#
@cli_server.command(name='start')
@click.option('--ip', default=None, help='ip address to listen on')
@click.option('-p', '--port', type=int, help='port to listen on')
@click.option('--debug', is_flag=True,
              help='run server in debug mode (auto-restart)')
@click_insert_context
def cli_server_start(ctx: ServerContext, ip: str, port: str,
                     debug: bool) -> None:
    """
    Start the server.

    Parameters
    ----------
    ctx : ServerContext
        The server context.
    ip : str
        The ip address to listen on.
    port : str
        The port to listen on.
    debug : bool
        Run server in debug mode (auto-restart).
    """
    info("Starting server.")

    # Run the server
    ip = ip or ctx.config['ip'] or '127.0.0.1'
    port = port or int(ctx.config['port']) or 5000
    info(f"ip: {ip}, port: {port}")
    app = ServerApp(ctx).start()
    run_dev_server(app, ip, port, debug=debug)


#
#   list
#
@cli_server.command(name='list')
def cli_server_configuration_list() -> None:
    """Print the available servers."""

    click.echo("\nName"+(21*" ")+"Environments"+(21*" ")+"System/User")
    click.echo("-"*70)

    sys_configs, f1 = ServerContext.available_configurations(
        system_folders=True)
    for config in sys_configs:
        click.echo(
            f"{config.name:25}{str(config.available_environments):32} System "
        )

    usr_configs, f2 = ServerContext.available_configurations(
        system_folders=False
    )
    for config in usr_configs:
        click.echo(
            f"{config.name:25}{str(config.available_environments):32} User   "
        )
    click.echo("-"*70)

    if len(f1)+len(f2):
        warning(
            f"{Fore.YELLOW}Number of failed imports: "
            f"{len(f1)+len(f2)}{Style.RESET_ALL}"
        )


#
#   files
#
@cli_server.command(name='files')
@click_insert_context
def cli_server_files(ctx: ServerContext) -> None:
    """
    List files locations of a server instance.

    Parameters
    ----------
    ctx : ServerContext
        The context of the server instance.
    """
    info(f"Configuration file = {ctx.config_file}")
    info(f"Log file           = {ctx.log_file}")
    info(f"Database           = {ctx.get_database_uri()}")


#
#   new
#
@cli_server.command(name='new')
@click.option('-n', '--name', default=None,
              help="name of the configutation you want to use.")
@click.option('-e', '--environment', default=S_ENV,
              help='configuration environment to use')
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False, default=S_FOL)
def cli_server_new(name: str, environment: str, system_folders: bool) -> None:
    """
    Create new server configuration.

    Parameters
    ----------
    name : str
        The name of the configuration.
    environment : str
        The environment of the configuration.
    system_folders : bool
        Whether to use system folders or not.
    """
    if not name:
        name = q.text("Please enter a configuration-name:").ask()
        name_new = name.replace(" ", "-")
        if name != name_new:
            info(f"Replaced spaces from configuration name: {name}")
            name = name_new

    # Check that we can write in this folder
    if not check_config_writeable(system_folders):
        error("Your user does not have write access to all folders. Exiting")
        exit(1)

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

    # create config in ctx location
    cfg_file = configuration_wizard(
        "server", name, environment, system_folders
    )
    info(f"New configuration created: {Fore.GREEN}{cfg_file}{Style.RESET_ALL}")

    # info(f"root user created.")
    info(
        f"You can start the server by "
        f"{Fore.GREEN}vserver start{Style.RESET_ALL}."
    )


#
#   import
#
@cli_server.command(name='import')
@click.argument('file_', type=click.Path(exists=True))
@click.option('--drop-all', is_flag=True, default=False)
@click_insert_context
def cli_server_import(ctx: ServerContext, file_: str, drop_all: bool) -> None:
    """
    Import organizations/collaborations/users and tasks. Mainly useful for
    testing purposes.

    Parameters
    ----------
    ctx : ServerContext
        The context of the server instance.
    file_ : str
        The YAML file with resources to import.
    drop_all : bool
        Whether to drop all tables before importing.
    """
    # Note: ctx appears to be unused but is needed for the click_insert_context
    # to select the server in which to import the data.
    info("Reading yaml file.")
    with open(file_) as f:
        entities = yaml.safe_load(f.read())

    info("Adding entities to database.")
    fixture.load(entities, drop_all=drop_all)


#
#   shell
#
@cli_server.command(name='shell')
@click_insert_context
def cli_server_shell(ctx: ServerContext) -> None:
    """
    Run an iPython shell.

    Note that using the shell is not recommended, as there are no checks on
    the validity of the data you are entering. It is better to use the UI,
    Python client, or the API.

    Parameters
    ----------
    ctx : ServerContext
        The context of the server instance.
    """
    # Note: ctx appears to be unused but is needed for the click_insert_context
    # to select the server and start the database connection.
    c = get_config()
    c.InteractiveShellEmbed.colors = "Linux"

    # Suppress logging (e.g. on tab-completion)
    import logging
    logging.getLogger('parso.cache').setLevel(logging.WARNING)
    logging.getLogger('parso.python.diff').setLevel(logging.WARNING)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    logging.warning(
        "Using the shell is not recommended! There are no checks on "
        "the validity of the data you are entering.")
    logging.warning("Please use the User interface, Python client, or API.")
    del logging

    import vantage6.server.db as db


    IPython.embed(config=c)


#
#   version
#
@cli_server.command(name='version')
def cli_server_version() -> None:
    """ Prints current version of vantage6 services installed. """
    click.echo(__version__)
