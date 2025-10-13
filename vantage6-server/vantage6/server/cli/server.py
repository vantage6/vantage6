from functools import wraps

import click
from colorama import Fore, Style

from vantage6.common import error
from vantage6.common.globals import InstanceType

from vantage6.cli.configuration_create import select_configuration_questionnaire
from vantage6.cli.context.server import ServerContext
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS as S_FOL

from vantage6.server import __version__
from vantage6.server.model.base import Database

help_ = {
    "name": "name of the configutation you want to use.",
    "config": "absolute path to configuration-file; overrides NAME",
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
    @click.option("-n", "--name", default=None, help=help_["name"])
    @click.option("-c", "--config", default=None, help=help_["config"])
    @click.option("--system", "system_folders", flag_value=True)
    @click.option("--user", "system_folders", flag_value=False, default=S_FOL)
    @wraps(func)
    def func_with_context(
        name: str, config: str, system_folders: bool, *args, **kwargs
    ) -> callable:
        # select configuration if none supplied
        if config:
            ctx = ServerContext.from_external_config_file(config, system_folders)
        else:
            if not name:
                try:
                    name = select_configuration_questionnaire(
                        InstanceType.SERVER, system_folders
                    )
                except Exception:
                    error("No configurations could be found!")
                    exit()

            # raise error if config could not be found
            if not ServerContext.config_exists(name, system_folders):
                scope = "system" if system_folders else "user"
                error(
                    f"Configuration {Fore.RED}{name}{Style.RESET_ALL} does not"
                    f" exist in the {Fore.RED}{scope}{Style.RESET_ALL} folder!"
                )
                exit(1)

            # create server context, and initialize db
            ctx = ServerContext(name, system_folders=system_folders, in_container=True)

        # initialize database (singleton)
        Database().connect(uri=ctx.get_database_uri(), allow_drop_all=False)

        return func(ctx, *args, **kwargs)

    return func_with_context


@click.group(name="server")
def cli_server() -> None:
    """Subcommand `vserver-local`."""
    pass


#
#   version
#
@cli_server.command(name="version")
def cli_server_version() -> None:
    """Prints current version of vantage6 services installed."""
    click.echo(__version__)
