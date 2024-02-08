from functools import wraps
import click

from vantage6.common import error
from vantage6.common.globals import InstanceType
from vantage6.cli.configuration_wizard import select_configuration_questionaire
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS
from vantage6.cli.context import select_context_class, get_context


# TODO to make this decorator usable by nodes as well, we should make the
# default for --user/--system configurable
def click_insert_context(type_: InstanceType) -> callable:
    """
    Supply the Click function with an additional context parameter. The context
    is passed to the function as the first argument.

    Parameters
    ----------
    type_ : InstanceType
        The type of instance for which the context should be inserted

    Returns
    -------
    Callable
        Click function with context

    Examples
    --------
    >>> @click_insert_context(InstanceType.SERVER)
    >>> def cli_server_start(ctx: ServerContext, *args, **kwargs) -> None:
    >>>     pass
    """

    def protection_decorator(func: callable) -> callable:
        @click.option("-n", "--name", default=None, help="Name of the configuration.")
        @click.option(
            "-c",
            "--config",
            default=None,
            help="Absolute path to " "configuration-file; overrides --name",
        )
        @click.option(
            "--system",
            "system_folders",
            flag_value=True,
            help="Use system folders instead of user folders. This " "is the default",
        )
        @click.option(
            "--user",
            "system_folders",
            flag_value=False,
            default=DEFAULT_SERVER_SYSTEM_FOLDERS,
            help="Use user folders instead of system folders",
        )
        @wraps(func)
        def decorator(
            name: str, config: str, system_folders: bool, *args, **kwargs
        ) -> callable:
            """
            Decorator function that adds the context to the function.

            Returns
            -------
            Callable
                Decorated function
            """
            ctx_class = select_context_class(type_)
            # path to configuration file always overrides name
            if config:
                ctx = ctx_class.from_external_config_file(config, system_folders)
            elif "ctx" in kwargs:
                # if ctx is already in kwargs (typically when one click command
                # calls another internally), use that existing ctx
                ctx = kwargs.pop("ctx")
            else:
                # in case no name, ctx or config file is supplied, ask the user
                # to select an existing config by name
                if not name:
                    try:
                        # select configuration if none supplied
                        name = select_configuration_questionaire(type_, system_folders)
                    except Exception:
                        error("No configurations could be found!")
                        exit(1)

                ctx = get_context(type_, name, system_folders)
            return func(ctx, *args, **kwargs)

        return decorator

    return protection_decorator
