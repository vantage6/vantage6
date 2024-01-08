import sys
import os
from vantage6.common.globals import STRING_ENCODING


def info(msg: str) -> None:
    """
    Print an info message to stdout.

    Parameters
    ----------
    msg : str
        Message to be printed
    """
    sys.stdout.write(f"info > {msg}\n")


def warn(msg: str) -> None:
    """
    Print a warning message to stdout.

    Parameters
    ----------
    msg : str
        Warning message to be printed
    """
    sys.stdout.write(f"warn > {msg}\n")


def error(msg: str) -> None:
    """
    Print an error message to stdout.

    Parameters
    ----------
    msg : str
        Error message to be printed
    """
    sys.stdout.write(f"error > {msg}\n")


def get_env_var(var_name: str, default: str | None = None) -> str:
    """
    Get the value of an environment variable. Environment variables are encoded
    by the node so they need to be decoded here.

    Parameters
    ----------
    var_name : str
        Name of the environment variable

    Returns
    -------
    var_value : str | None
        Value of the environment variable, or default value if not found
    """
    try:
        # encode with latin1 which is round trip encoding i.e. encoding doesnt
        # change the value
        return os.environ[var_name].encode('latin1').decode(STRING_ENCODING)
    except KeyError:
        return default
