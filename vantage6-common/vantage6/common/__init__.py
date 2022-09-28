import os
import base64
import click
import appdirs
import ipaddress

from colorama import init, Fore, Style

from vantage6.common.globals import STRING_ENCODING


# init colorstuff
init()


def logger_name(special__name__):
    log_name = special__name__.split('.')[-1]
    if len(log_name) > 14:
        log_name = log_name[:11] + ".."
    return log_name


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super(Singleton, cls).__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


def bytes_to_base64s(bytes_):
    """Return bytes as base64 encoded string."""
    return base64.b64encode(bytes_).decode(STRING_ENCODING)


def base64s_to_bytes(bytes_string):
    """Return base64 encoded string as bytes."""
    return base64.b64decode(bytes_string.encode(STRING_ENCODING))


#
# CLI prints
#
def echo(msg, level="info"):
    type_ = {
        "error": f"[{Fore.RED}error{Style.RESET_ALL}]",
        "warn": f"[{Fore.YELLOW}warn{Style.RESET_ALL}]",
        "info": f"[{Fore.GREEN}info{Style.RESET_ALL}]",
        "debug": f"[{Fore.CYAN}debug{Style.RESET_ALL}]",
    }.get(level)
    click.echo(f"{type_:16} - {msg}")


def info(msg):
    echo(msg, "info")


def warning(msg):
    echo(msg, "warn")


def error(msg):
    echo(msg, "error")


def debug(msg):
    echo(msg, "debug")


class ClickLogger:
    """"Logs output to the click interface."""

    @staticmethod
    def info(msg):
        info(msg)

    @staticmethod
    def warn(msg):
        warning(msg)

    @staticmethod
    def error(msg):
        error(msg)

    @staticmethod
    def debug(msg):
        debug(msg)


def check_config_write_permissions(system_folders=False):
    dirs = appdirs.AppDirs()
    if system_folders:
        dirs_to_check = [
            dirs.site_config_dir
        ]
    else:
        dirs_to_check = [
            dirs.user_config_dir
        ]
    w_ok = True
    for dir_ in dirs_to_check:
        if not os.access(dir_, os.W_OK):
            warning(f"No write permissions at '{dir_}'")
            w_ok = False

    return w_ok


def check_write_permissions(folder):
    w_ok = True
    if not os.access(folder, os.W_OK):
        warning(f"No write permissions at '{folder}'")
        w_ok = False

    return w_ok


def is_ip_address(ip: str) -> bool:
    """Test if input IP address is a valid IP address

    Parameters
    ----------
    ip: str
        IP address to validate

    Returns
    -------
    bool: whether or not IP address is valid
    """
    try:
        _ = ipaddress.ip_address(ip)
        return True
    except Exception:
        return False
