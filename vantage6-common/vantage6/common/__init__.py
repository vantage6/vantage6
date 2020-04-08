import base64
import click

from colorama import init, Fore, Back, Style

from vantage6.common.globals import STRING_ENCODING

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
    return base64.b64encode(bytes_).decode(STRING_ENCODING)


def base64s_to_bytes(bytes_string):
    return base64.b64decode(bytes_string.encode(STRING_ENCODING))


#
# CLI prints
#
def echo(msg, level = "info"):
    type_ = {
        "error": f"[{Fore.RED}error{Style.RESET_ALL}]",
        "warn": f"[{Fore.YELLOW}warn{Style.RESET_ALL}]",
        "info": f"[{Fore.GREEN}info{Style.RESET_ALL}]",
        "debug": f"[{Fore.CYAN}debug{Style.RESET_ALL}]",
    }.get(level)
    click.echo(f"{type_} - {msg}")


def info(msg):
    echo(msg, "info")


def warning(msg):
    echo(msg, "warn")


def error(msg):
    echo(msg, "error")
