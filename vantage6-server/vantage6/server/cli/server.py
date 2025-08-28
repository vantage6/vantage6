from functools import wraps

import click
import IPython
import yaml
from colorama import Fore, Style
from traitlets.config import get_config

from vantage6.common import (
    error,
    info,
)
from vantage6.common.globals import InstanceType

from vantage6.cli.configuration_wizard import select_configuration_questionaire
from vantage6.cli.context.server import ServerContext
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS as S_FOL

from vantage6.server import __version__
from vantage6.server.controller import fixture
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
                    name = select_configuration_questionaire(
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
#   import
#
@cli_server.command(name="import")
@click.argument("file_", type=click.Path(exists=True))
@click.option("--drop-all", is_flag=True, default=False)
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
    # TODO v5+ this will probably no longer work since API keys are no longer in here
    # Should we get rid of this command or make something new? Also delete load()
    # function if we remove it. See issue #2023
    fixture.load(entities, drop_all=drop_all)


#
#   shell
#
@cli_server.command(name="shell")
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

    logging.getLogger("parso.cache").setLevel(logging.WARNING)
    logging.getLogger("parso.python.diff").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.warning(
        "Using the shell is not recommended! There are no checks on "
        "the validity of the data you are entering."
    )
    logging.warning("Please use the User interface, Python client, or API.")
    del logging

    import vantage6.server.db as db  # noqa: F401

    IPython.embed(config=c)


#
#   version
#
@cli_server.command(name="version")
def cli_server_version() -> None:
    """Prints current version of vantage6 services installed."""
    click.echo(__version__)
