from functools import wraps
from pathlib import Path

import click

from vantage6.common import error
from vantage6.common.globals import SANDBOX_SUFFIX, InstanceType

from vantage6.cli.configuration_create import select_configuration_questionnaire
from vantage6.cli.context import get_context, select_context_class


def click_insert_context(
    type_: InstanceType,
    include_name: bool = False,
    include_system_folders: bool = False,
    is_sandbox: bool = False,
    sandbox_param: str | None = None,
) -> callable:
    """
    Supply the Click function with an additional context parameter. The context
    is passed to the function as the first argument.

    Parameters
    ----------
    type_ : InstanceType
        The type of instance for which the context should be inserted
    include_name : bool
        Include the name of the configuration as an argument
    include_system_folders : bool
        Include whether or not to use the system folders as an argument
    is_sandbox : bool
        Include whether or not to use the sandbox configurations as an argument
    sandbox_param : str | None
        Name of a Click option/parameter in the command function whose boolean
        value should determine sandbox mode at runtime. If provided, this value
        overrides the static is_sandbox parameter.

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
            help="Path to configuration-file; overrides --name",
        )
        @click.option(
            "--system",
            "system_folders",
            flag_value=True,
            help="Use system folders instead of user folders. This is the default",
        )
        @click.option(
            "--user",
            "system_folders",
            flag_value=False,
            default=False if type_ == InstanceType.NODE or is_sandbox else True,
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

            # Determine sandbox mode, preferring runtime option when provided
            runtime_is_sandbox = is_sandbox
            if sandbox_param is not None:
                # Pop to avoid passing unknown kwarg to the wrapped function
                runtime_is_sandbox = bool(kwargs.pop(sandbox_param, False))
            if runtime_is_sandbox and name and name.endswith(SANDBOX_SUFFIX):
                name = name[: -len(SANDBOX_SUFFIX)]

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
                        name = select_configuration_questionnaire(
                            type_, system_folders, runtime_is_sandbox
                        )
                    except Exception:
                        error("No configurations could be found!")
                        exit(1)

                ctx = get_context(type_, name, system_folders, runtime_is_sandbox)
            extra_args = []
            if include_name:
                if not name:
                    name = Path(config).stem
                extra_args.append(name)
            if include_system_folders:
                extra_args.append(system_folders)
            return func(ctx, *extra_args, *args, **kwargs)

        return decorator

    return protection_decorator
