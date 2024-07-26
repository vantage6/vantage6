import os
import pyarrow as pa
import pandas as pd

from typing import Any
from datetime import datetime
from functools import wraps

from vantage6.common import error, debug, info
from vantage6.common.enums import LocalAction
from vantage6.algorithm.tools.exceptions import (
    DataTypeError,
    SessionError,
    EnvironmentVariableNotFoundError,
)
from vantage6.algorithm.tools.util import get_action


def _exit_if_action_mismatch(function_action: LocalAction):
    """
    Check if the requested action matches the container action.

    Parameters
    ----------
    function_action : LocalAction
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
            f"{function_action}. "
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
        If the data extraction function returns an unsupported data frame type.
    """
    info("Converting algorithm output to a Parquet Table.")
    info(data)
    match type(data):

        case pd.DataFrame:
            try:
                data = pa.Table.from_pandas(data)
            except Exception as e:
                raise SessionError(
                    f"Could not convert DataFrame to Parquet Table"
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

    @wraps(func)
    def wrapper(*args, **kwargs) -> None:

        # Validate that the correct action is invoked in combination with the function
        # that is wrapped by this decorator.
        _exit_if_action_mismatch(LocalAction.DATA_EXTRACTION)

        # TODO: should we add the data in here??
        result = func(*args, **kwargs)

        return _convert_to_parquet(result)

    return wrapper


def pre_processing(func: callable):

    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:

        # Validate that the correct action is invoked in combination with the function
        # that is wrapped by this decorator.
        _exit_if_action_mismatch(LocalAction.PREPROCESSING)

        # TODO should we add the data in here??
        result = func(*args, **kwargs)

        return _convert_to_parquet(result)

    return wrapper


def federated(func: callable):

    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        _exit_if_action_mismatch(LocalAction.COMPUTE)
        result = func(*args, **kwargs)
        return result

    return wrapper


def central(func: callable):

    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        _exit_if_action_mismatch(LocalAction.COMPUTE)
        result = func(*args, **kwargs)
        return result

    return wrapper
