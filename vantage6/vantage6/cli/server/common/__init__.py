from typing import Iterable
from functools import wraps

from docker.client import DockerClient
import click
from colorama import Fore, Style

from vantage6.common import error, info
from vantage6.common.globals import STRING_ENCODING, APPNAME
from vantage6.common.docker.addons import remove_container, get_container

from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS
from vantage6.cli.context import ServerContext
from vantage6.cli.configuration_wizard import select_configuration_questionaire


def click_insert_context(func: callable) -> callable:
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
                  help="Name of the configuration you want to use.")
    @click.option('-c', '--config', default=None,
                  help='Absolute path to configuration-file; overrides NAME')
    @click.option('--system', 'system_folders', flag_value=True,
                  help='Use system folders instead of user folders. This is '
                  'the default')
    @click.option('--user', 'system_folders', flag_value=False,
                  default=DEFAULT_SERVER_SYSTEM_FOLDERS,
                  help='Use user folders instead of system folders')
    @wraps(func)
    def func_with_context(name: str, config: str, system_folders: bool, *args,
                          **kwargs) -> callable:
        """
        Decorator function that adds the context to the function.

        Returns
        -------
        Callable
            Decorated function
        """
        # path to configuration file always overrides name
        if config:
            ctx = ServerContext.from_external_config_file(
                config,
                system_folders
            )
        elif 'ctx' in kwargs:
            # if ctx is already in kwargs (typically when one click command
            # calls another internally), use that existing ctx
            ctx = kwargs.pop('ctx')
        else:
            # in case no name, ctx or config file is supplied, ask the user to
            # select an existing config by name
            if not name:
                try:
                    # select configuration if none supplied
                    name = select_configuration_questionaire(
                        "server", system_folders
                    )
                except Exception:
                    error("No configurations could be found!")
                    exit(1)

            ctx = get_server_context(name, system_folders)
        return func(ctx, *args, **kwargs)

    return func_with_context


def get_server_context(name: str, system_folders: bool) \
        -> ServerContext:
    """
    Load the server context from the configuration file.

    Parameters
    ----------
    name : str
        Name of the server to inspect
    system_folders : bool
        Wether to use system folders or if False, the user folders

    Returns
    -------
    ServerContext
        Server context object
    """
    if not ServerContext.config_exists(name, system_folders):
        scope = "system" if system_folders else "user"
        error(
            f"Configuration {Fore.RED}{name}{Style.RESET_ALL} does not "
            f"exist in the {Fore.RED}{scope}{Style.RESET_ALL} folders!"
        )
        exit(1)

    # We do not want to log this here, we do this in the container and not on
    # the host. We only want CLI logging here.
    ServerContext.LOGGING_ENABLED = False

    # create server context, and initialize db
    ctx = ServerContext(name, system_folders=system_folders)

    return ctx


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
        info(f"Stopped the {Fore.GREEN}{ui_container_name}"
             f"{Style.RESET_ALL} User Interface container.")
