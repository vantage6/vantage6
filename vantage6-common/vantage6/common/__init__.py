"""
Common functionality used in multiple vantage6 components.
"""

import base64
import importlib.metadata
import os
import typing
import uuid

import appdirs
import click
from colorama import Fore, Style, init

from vantage6.common.enum import StrEnumBase
from vantage6.common.globals import APPNAME, STRING_ENCODING

__version__ = importlib.metadata.version(__package__)

# init colorstuff
init()


def logger_name(special__name__: str):
    """
    Return the name of the logger.

    Parameters
    ----------
    special__name__: str
        The __name__ variable of a module.

    Returns
    -------
    str
        The name of the logger.
    """
    log_name = special__name__.split(".")[-1]
    if len(log_name) > 14:
        log_name = log_name[:11] + ".."
    return log_name


class WhoAmI(typing.NamedTuple):
    """
    Data-class to store Authenticatable information in.

    Attributes
    ----------
    type_: str
        The type of the authenticatable (user or node).
    id_: int
        The id of the authenticatable.
    name: str
        The name of the authenticatable.
    organization_name: str
        The name of the organization of the authenticatable.
    organization_id: int
        The id of the organization of the authenticatable.
    """

    type_: str
    id_: int
    name: str
    organization_name: str
    organization_id: int

    def __repr__(self) -> str:
        return (
            f"<WhoAmI "
            f"name={self.name}, "
            f"type={self.type_}, "
            f"organization={self.organization_name}, "
            f"(id={self.organization_id})"
            ">"
        )


class Singleton(type):
    """
    Singleton metaclass. It allows us to create just a single instance of a
    class to which it is the metaclass.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs) -> object:
        """
        When the class is called, return an instance of the class. If the
        instance already exists, return that instance.
        """
        if cls not in cls._instances:
            instance = super(Singleton, cls).__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


def bytes_to_base64s(bytes_: bytes) -> str:
    """
    Convert bytes into base64 encoded string.

    Parameters
    ----------
    bytes_: bytes
        The bytes to convert.

    Returns
    -------
    str
        The base64 encoded string.
    """
    return base64.b64encode(bytes_).decode(STRING_ENCODING)


def base64s_to_bytes(bytes_string: str) -> bytes:
    """
    Convert base64 encoded string to bytes.

    Parameters
    ----------
    bytes_string: str
        The base64 encoded string.

    Returns
    -------
    bytes
        The encoded string converted to bytes.
    """
    return base64.b64decode(bytes_string.encode(STRING_ENCODING))


#
# CLI prints
#
def echo(msg: str, level: str = "info") -> None:
    """
    Print a message to the CLI.

    Parameters
    ----------
    msg: str
        The message to print.
    level: str
        The level of the message. Can be one of: "error", "warn", "info",
        "debug".
    """
    type_ = {
        "error": f"[{Fore.RED}error{Style.RESET_ALL}]",
        "warn": f"[{Fore.YELLOW}warn {Style.RESET_ALL}]",
        "info": f"[{Fore.GREEN}info {Style.RESET_ALL}]",
        "debug": f"[{Fore.CYAN}debug{Style.RESET_ALL}]",
    }.get(level)
    click.echo(f"{type_:16} - {msg}")


def info(msg: str) -> None:
    """
    Print an info message to the CLI.

    Parameters
    ----------
    msg: str
        The message to print.
    """
    echo(msg, "info")


def warning(msg: str) -> None:
    """
    Print a warning message to the CLI.

    Parameters
    ----------
    msg: str
        The message to print.
    """
    echo(msg, "warn")


def error(msg: str) -> None:
    """
    Print an error message to the CLI.

    Parameters
    ----------
    msg: str
        The message to print.
    """
    echo(msg, "error")


def debug(msg: str) -> None:
    """
    Print a debug message to the CLI.

    Parameters
    ----------
    msg: str
        The message to print.
    """
    echo(msg, "debug")


class ClickLogger:
    """ "Logs output to the click interface."""

    @staticmethod
    def info(msg: str) -> None:
        """
        Print an info message to the click interface.

        Parameters
        ----------
        msg: str
            The message to print.
        """
        info(msg)

    @staticmethod
    def warn(msg: str) -> None:
        """
        Print a warning message to the click interface.

        Parameters
        ----------
        msg: str
            The message to print.
        """
        warning(msg)

    @staticmethod
    def error(msg: str) -> None:
        """
        Print an error message to the click interface.

        Parameters
        ----------
        msg: str
            The message to print.
        """
        error(msg)

    @staticmethod
    def debug(msg: str) -> None:
        """
        Print a debug message to the click interface.

        Parameters
        ----------
        msg: str
            The message to print.
        """
        debug(msg)


def ensure_config_dir_writable(system_folders: bool = False) -> bool:
    """
    Check if the user has write permissions to create the configuration file.

    Parameters
    ----------
    system_folders: bool
        Whether to check the system folders or the user folders.

    Returns
    -------
    bool
        Whether the user has write permissions to create the configuration
        file or not.
    """
    dirs = appdirs.AppDirs()
    config_dir = get_config_path(dirs, system_folders=system_folders)
    w_ok = True
    if not os.path.isdir(config_dir):
        warning(
            f"Target directory '{config_dir}' for configuration file does not exist."
            " Attempting to create it."
        )
        try:
            os.makedirs(config_dir)
            w_ok = True
        except Exception as e:
            error(f"Could not create directory '{config_dir}': {e}")
            w_ok = False
    elif not os.access(config_dir, os.W_OK):
        warning(f"No write permissions at '{config_dir}'.")
        w_ok = False

    return w_ok


def get_config_path(dirs: appdirs.AppDirs, system_folders: bool = False) -> str:
    """
    Get the path to the configuration directory.

    Parameters
    ----------
    dirs: appdirs.AppDirs
        The appdirs object.
    system_folders: bool
        Whether to get path to the system folders or the user folders.

    Returns
    -------
    str
        The path to the configuration directory.
    """
    if system_folders:
        config_dir = dirs.site_config_dir
        # the Appdirs package prefers to store the config in /etc/xdg, but
        # we chose instead to put it in /etc/vantage6. We think this is more
        # in accordance with the Unix File Hierarchy Standard for config files.
        if "xdg" in config_dir:
            config_dir = f"/etc/{APPNAME}"
        return config_dir
    else:
        return dirs.user_config_dir


def generate_apikey() -> str:
    """Creates random api_key using uuid.

    Returns
    -------
    str
        api_key
    """
    return str(uuid.uuid4())


def split_rabbitmq_uri(rabbit_uri: str) -> dict:
    """
    Get details (user, pass, host, vhost, port) from a RabbitMQ uri.

    Parameters
    ----------
    rabbit_uri: str
        URI of RabbitMQ service ('amqp://$user:$pass@$host:$port/$vhost')

    Returns
    -------
    dict[str]
        The vhost defined in the RabbitMQ URI
    """
    (user_details, location_details) = rabbit_uri.split("@", 1)
    (user, password) = user_details.split("/")[-1].split(":", 1)
    (host, remainder) = location_details.split(":", 1)
    port, vhost = remainder.split("/", 1)
    return {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "vhost": vhost,
    }


def validate_required_env_vars(env_vars: StrEnumBase) -> None:
    """Validate that the required environment variables are set."""
    for env_var in env_vars.list():
        if not os.environ.get(env_var):
            raise ValueError(f"Required environment variable '{env_var}' is not set")
