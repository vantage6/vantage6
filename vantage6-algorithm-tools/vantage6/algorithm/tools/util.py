import sys
import os
import base64
import binascii

from vantage6.common.globals import STRING_ENCODING, ENV_VAR_EQUALS_REPLACEMENT


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


# TODO v5+ move this function to wrap.py and no longer expose it to be used by
# algorithms but as part of _decode_env_vars. It is kept here for backwards
# compatibility with 4.2/4.3 algorithms
def get_env_var(var_name: str, default: str | None = None) -> str:
    """
    Get the value of an environment variable. Environment variables are encoded
    by the node so they need to be decoded here.

    Note that this decoding follows the reverse of the encoding in the node:
    first replace '=' back and then decode the base32 string.

    Parameters
    ----------
    var_name : str
        Name of the environment variable
    default : str | None
        Default value to return if the environment variable is not found

    Returns
    -------
    var_value : str | None
        Value of the environment variable, or default value if not found
    """
    try:
        encoded_env_var_value = (
            os.environ[var_name]
            .replace(ENV_VAR_EQUALS_REPLACEMENT, "=")
            .encode(STRING_ENCODING)
        )
        return base64.b32decode(encoded_env_var_value).decode(STRING_ENCODING)
    except KeyError:
        return default
    except binascii.Error:
        # If the decoding fails, return the original value
        return os.environ[var_name]
