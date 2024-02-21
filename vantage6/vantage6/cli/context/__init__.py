"""
The context module in the CLI package contains the Context classes of instances
started from the CLI, such as nodes and servers. These contexts are related to
the host system and therefore part of the CLI package.

All classes are derived from the abstract AppContext class and provide the
vantage6 applications with naming conventions, standard file locations, and
more.
"""

from colorama import Fore, Style

from vantage6.common.globals import InstanceType
from vantage6.common import error
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.context.server import ServerContext


def select_context_class(
    type_: InstanceType,
) -> ServerContext | NodeContext | AlgorithmStoreContext:
    """
    Select the context class based on the type of instance.

    Parameters
    ----------
    type_ : InstanceType
        The type of instance for which the context should be inserted

    Returns
    -------
    ServerContext | NodeContext | AlgorithmStoreContext
        Specialized subclass of AppContext for the given instance type

    Raises
    ------
    NotImplementedError
        If the type_ is not implemented
    """
    if type_ == InstanceType.SERVER:
        return ServerContext
    elif type_ == InstanceType.ALGORITHM_STORE:
        return AlgorithmStoreContext
    elif type_ == InstanceType.NODE:
        return NodeContext
    else:
        raise NotImplementedError


def get_context(
    type_: InstanceType, name: str, system_folders: bool
) -> ServerContext | NodeContext | AlgorithmStoreContext:
    """
    Load the server context from the configuration file.

    Parameters
    ----------
    type_ : InstanceType
        The type of instance to get the context for
    name : str
        Name of the instance
    system_folders : bool
        Wether to use system folders or if False, the user folders

    Returns
    -------
    AppContext
        Specialized subclass context of AppContext for the given instance type
    """
    ctx_class = select_context_class(type_)
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
