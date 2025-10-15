import os
from contextlib import contextmanager


@contextmanager
def env_vars(**kwargs):
    """
    Context manager to temporarily set environment variables

    Parameters
    ----------
    kwargs : dict
        Dictionary of environment variables to set

    Example
    -------
    Overwrite an existing environment variable and restore after the context manager is
    exited:
    >>> import os
    >>> os.environ["TEST_ENV_VAR"] = "original"
    >>> with env_vars(TEST_ENV_VAR="temporary"):
    >>>     print(os.environ["TEST_ENV_VAR"])
    >>> temporary
    >>> print(os.environ["TEST_ENV_VAR"])
    >>> original

    Set a new environment variable within the context scope:
    >>> with env_vars(TEST_ENV_VAR="temporary"):
    >>>     print(os.environ["TEST_ENV_VAR"])
    >>> temporary
    >>> print("TEST_ENV_VAR" in os.environ)
    >>> False
    """

    old_values = {}
    try:
        for key, value in kwargs.items():
            old_values[key] = os.environ.get(key)
            os.environ[key] = str(value)
        yield
    finally:
        for key, old_value in old_values.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value
