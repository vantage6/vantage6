from colorama import Fore, Style

from vantage6.common import error
from vantage6.common.context import AppContext


def get_server_context(
    name: str, system_folders: bool, ctx_class: AppContext
) -> AppContext:
    """
    Load the server context from the configuration file.

    Parameters
    ----------
    name : str
        Name of the server to inspect
    system_folders : bool
        Wether to use system folders or if False, the user folders
    ctx_class : AppContext
        Context class to be used. Derivative of AppContext class

    Returns
    -------
    ServerContext
        Server context object
    """
    if not ctx_class.config_exists(name, system_folders):
        scope = "system" if system_folders else "user"
        error(
            f"Configuration {Fore.RED}{name}{Style.RESET_ALL} does not "
            f"exist in the {Fore.RED}{scope}{Style.RESET_ALL} folders!"
        )
        exit(1)

    # We do not want to log this here, we do this in the container and not on
    # the host. We only want CLI logging here.
    ctx_class.LOGGING_ENABLED = False

    # create server context, and initialize db
    ctx = ctx_class(name, system_folders=system_folders)

    return ctx
