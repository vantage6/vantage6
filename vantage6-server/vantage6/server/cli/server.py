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
    check_config_write_permissions
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


def click_insert_context(func):

    # add option decorators
    @click.option('-n', '--name', default=None, help=help_["name"])
    @click.option('-c', '--config', default=None, help=help_["config"])
    @click.option('-e', '--environment', default=S_ENV, help=help_["env"])
    @click.option('--system', 'system_folders', flag_value=True)
    @click.option('--user', 'system_folders', flag_value=False, default=S_FOL)
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
def cli_server():
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
def cli_server_start(ctx, ip, port, debug):
    """Start the server."""

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
def cli_server_configuration_list():
    """Print the available configurations."""

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
@click.option('-e', '--environment', default=S_ENV,
              help='configuration environment to use')
@click.option('--system', 'system_folders', flag_value=True)
@click.option('--user', 'system_folders', flag_value=False, default=S_FOL)
def cli_server_new(name, environment, system_folders):
    """Create new configuration."""

    if not name:
        name = q.text("Please enter a configuration-name:").ask()
        name_new = name.replace(" ", "-")
        if name != name_new:
            info(f"Replaced spaces from configuration name: {name}")
            name = name_new

    # Check that we can write in this folder
    if not check_config_write_permissions(system_folders):
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
def cli_server_import(ctx, file_, drop_all):
    """ Import organizations/collaborations/users and tasks.

        Especially usefull for testing purposes.
    """
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
def cli_server_shell(ctx):
    """ Run a iPython shell. """
    # shell.init(ctx.environment)
    c = get_config()
    c.InteractiveShellEmbed.colors = "Linux"

    # Suppress logging (e.g. on tab-completion)
    import logging
    logging.getLogger('parso.cache').setLevel(logging.WARNING)
    logging.getLogger('parso.python.diff').setLevel(logging.WARNING)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    del logging

    import vantage6.server.db as db

    IPython.embed(config=c)


#
#   version
#
@cli_server.command(name='version')
def cli_server_version():
    """Returns current version of vantage6 services installed."""
    click.echo(__version__)
