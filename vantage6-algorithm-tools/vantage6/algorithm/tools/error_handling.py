import logging
from collections.abc import Callable
from functools import wraps

from vantage6.common import logger_name

from vantage6.algorithm.tools.exceptions import AlgorithmError, AlgorithmRuntimeError

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def handle_data_errors(func: Callable) -> Callable:
    """
    Decorator to catch errors from data manipulation in algorithm functions and
    prevent leaking privacy-sensitive data via error messages or tracebacks.

    Any exception that is not a vantage6 ``AlgorithmError`` is replaced by a generic
    ``AlgorithmRuntimeError``. This includes non-pandas exceptions such as
    ``ValueError`` or ``KeyError``, which are commonly raised by pandas operations and
    tend to contain data values in their message.

    The vantage6 ``AlgorithmError`` exceptions are re-raised unchanged: their messages
    are written by algorithm developers and are meant to be shown to the user.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AlgorithmError:
            raise
        except Exception as e:  # noqa: BLE001
            msg = (
                f"An error of type {type(e).__name__} occurred in "
                f"'{func.__qualname__}'. Details have been omitted to protect privacy."
            )
            log.error(msg)
            # `from None` suppresses the exception context: without it, the original
            # exception, including its message, is still printed when the traceback
            # is logged
            raise AlgorithmRuntimeError(msg) from None

    return wrapper


# Backwards-compatible alias
handle_pandas_errors = handle_data_errors
