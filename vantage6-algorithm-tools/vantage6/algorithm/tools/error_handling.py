import logging
from functools import wraps

import pandas as pd

from vantage6.common import logger_name

from vantage6.algorithm.tools.exceptions import AlgorithmRuntimeError

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def _collect_pandas_error_types() -> tuple[type, ...]:
    """
    Collect all exception classes exported from pandas.errors.

    Returns a tuple of exception types to be used in an except clause.
    """
    exception_types = []
    errors_module = pd.errors
    for attr_name in errors_module.__all__:
        attr = getattr(errors_module, attr_name, None)
        if isinstance(attr, type) and issubclass(attr, Exception):
            exception_types.append(attr)

    return tuple(exception_types)


PANDAS_ERROR_TYPES = _collect_pandas_error_types()


def handle_pandas_errors(func):
    """
    Decorator to catch pandas-related errors from algorithm functions and
    prevent leaking privacy-sensitive data via tracebacks.

    - Catches pandas-specific exceptions and common data-manipulation errors.
    - Logs a minimal, non-identifying message (no traceback, no exception str).
    - Returns a safe, generic error response with 400 Bad Request.
    - Other unexpected exceptions continue to log with traceback for debugging.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PANDAS_ERROR_TYPES as e:
            # Avoid logging tracebacks or exception messages that may contain data
            msg = (
                f"Pandas-related error of type {type(e).__name__} occurred in "
                "algorithm function. Details have been omitted to protect privacy."
            )
            log.error(msg)
            # pylint: disable=raise-missing-from
            raise AlgorithmRuntimeError(msg)

    return wrapper
