import pyarrow as pa
import pandas as pd

from typing import Any
from functools import wraps

from vantage6.common import info
from vantage6.common.enum import AlgorithmStepType
from vantage6.algorithm.tools.exceptions import (
    DataTypeError,
    SessionError,
)
from vantage6.algorithm.tools.util import get_action


def _exit_if_action_mismatch(function_action: AlgorithmStepType):
    """
    Check if the requested action matches the container action.

    Each container is started with a specific action type. For example, if the user
    requests a data extraction, the container is started with the data extraction
    action. This function checks if the requested action matches the container action.

    The user requests these different actions by using different endpoints, therefore
    we need to validate that the container/method the user requested is actually
    performing the correct action.

    Parameters
    ----------
    function_action : AlgorithmStepType
        The action requested by the user.

    Raises
    ------
    EnvironmentVariableNotFoundError
        If the environment variable FUNCTION_ACTION is not found.
    SessionError
        If the container action does not match the requested action.

    """
    info(f"Validating function action: {function_action}")
    requested_action = get_action()

    if requested_action != function_action:
        raise SessionError(
            f"Container started as {requested_action}, but user requested "
            f"{function_action}."
        )


def _convert_to_parquet(data: Any) -> pa.Table:
    """
    Convert the algorithm output to a Parquet Table.

    Parameters
    ----------
    data : Any
        The algorithm output data.

    Returns
    -------
    pa.Table
        The converted Parquet Table.

    Raises
    ------
    SessionError
        If the DataFrame cannot be converted to a Parquet Table.
    DataTypeError
        If the data extraction function returns an unsupported dataframe type.
    """
    info("Converting algorithm output to a Parquet Table.")
    match type(data):

        case pd.DataFrame:
            try:
                data = pa.Table.from_pandas(data)
            except Exception as e:
                raise SessionError(
                    "Could not convert DataFrame to Parquet Table"
                ) from e
            return data

        case pa.Table:
            return data
        case _:
            raise DataTypeError(
                "Data extraction function did not return a supported data "
                f"frame type. Got {type(data)} instead. Supported types are: "
                "pandas.DataFrame, pyarrow.Table."
            )


def data_extraction(func: callable) -> callable:
    """Decorator for data extraction functions."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:

        # Validate that the correct action is invoked in combination with the function
        # that is wrapped by this decorator.
        _exit_if_action_mismatch(AlgorithmStepType.DATA_EXTRACTION)

        # TODO: should we add the data in here??
        result = func(*args, **kwargs)

        return _convert_to_parquet(result)

    return wrapper


def pre_processing(func: callable) -> callable:
    """Decorator for pre-processing functions."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:

        # Validate that the correct action is invoked in combination with the function
        # that is wrapped by this decorator.
        _exit_if_action_mismatch(AlgorithmStepType.PREPROCESSING)

        result = func(*args, **kwargs)

        return _convert_to_parquet(result)

    return wrapper


def federated(func: callable) -> callable:
    """Decorator for federated functions."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        _exit_if_action_mismatch(AlgorithmStepType.COMPUTE)
        result = func(*args, **kwargs)
        return result

    return wrapper


def central(func: callable) -> callable:
    """Decorator for central functions."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        _exit_if_action_mismatch(AlgorithmStepType.COMPUTE)
        result = func(*args, **kwargs)
        return result

    return wrapper
