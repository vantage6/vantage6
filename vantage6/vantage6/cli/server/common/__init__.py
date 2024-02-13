from docker.client import DockerClient
from colorama import Fore, Style

from vantage6.common import error, info
from vantage6.common.globals import APPNAME
from vantage6.common.docker.addons import remove_container, get_container
from vantage6.common.context import AppContext

from vantage6.cli.context.server import ServerContext


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


def stop_ui(client: DockerClient, ctx: ServerContext) -> None:
    """
    Check if the UI container is running, and if so, stop and remove it.

    Parameters
    ----------
    client : DockerClient
        Docker client
    ctx : ServerContext
        Server context object
    """
    ui_container_name = f"{APPNAME}-{ctx.name}-{ctx.scope}-ui"
    ui_container = get_container(client, name=ui_container_name)
    if ui_container:
        remove_container(ui_container, kill=True)
        info(
            f"Stopped the {Fore.GREEN}{ui_container_name}"
            f"{Style.RESET_ALL} User Interface container."
        )
