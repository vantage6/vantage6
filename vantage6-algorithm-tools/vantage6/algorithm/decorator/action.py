import os
from functools import wraps
from typing import Any

import pandas as pd
import pyarrow as pa

from vantage6.common import error, info
from vantage6.common.enum import AlgorithmStepType
from vantage6.common.globals import ContainerEnvNames

from vantage6.algorithm.tools.exceptions import (
    DataTypeError,
    SessionActionMismatchError,
)
from vantage6.algorithm.tools.util import get_action, get_env_var


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
    SessionActionMismatchError
        If the container action does not match the requested action.

    """
    info(f"Validating function action: {function_action.value}")
    requested_action = get_action()

    if requested_action != function_action:
        raise SessionActionMismatchError(
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
    SessionActionMismatchError
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
                raise SessionActionMismatchError(
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
    @wraps(func)
    def wrapper(
        *args, mock_uri: str | None = None, mock_type: str | None = None, **kwargs
    ) -> pa.Table:
        """
        Decorator for data extraction functions.

        The user can request different databases that correspond to the different data
        sources that are available at each node.

        Parameters
        ----------
        mock_uri : str
            Mock URI to use instead of the regular URI
        mock_type : str
            Mock type to use, e.g. `csv`, `excel`, `other`, etc.

        Returns
        -------
        pa.Table
            The converted Parquet Table.

        Raises
        ------
        SessionActionMismatchError
            If the container action does not match the requested action.
        DataTypeError
            If the data extraction function returns an unsupported dataframe type.
        EnvironmentVariableNotFoundError
            If the environment variable FUNCTION_ACTION is not found.

        Examples
        --------
        For a PostgreSQL database, the connection details are retrieved by the node from
        the environment variables and passed on to the algorithm container. This always
        follows the `DATABASE_*` naming convention.

        When the node configuration lists a URI, username, password for database A, the
        node creates the following environment for database A:
        ```bash
        DATABASE_A_URI="postgresql://host:port/database"
        DATABASE_A_USERNAME="postgresql"
        DATABASE_A_PASSWORD="password"
        ```

        When the user then requests a task for database A, the node will pass the
        following the following environment variables to the algorithm container (note
        that the `A_` annotation is removed):
        ```bash
        DATABASE_URI="postgresql://host:port/database"
        DATABASE_USERNAME="postgresql"
        DATABASE_PASSWORD="password"
        ```

        This decorator uses those environment variables to connect to the database

        ```python
        >>> @data_extraction
        >>> def my_function(connection_details: str):
        >>>     print(connection_details)
        {
            "uri": "postgresql://host:port/database",
            "username": "postgresql",
            "password": "password",
        }
        >>>>    # some more code here, and eventually return a pandas DataFrame
        >>>>    return pd.DataFrame({"a": [1, 2, 3]})
        ```

        The node will convert the pandas DataFrame to a parquet file on the node, which
        can be used by other algorithms in the session.
        """

        # Validate that the correct action is invoked in combination with the function
        # that is wrapped by this decorator.
        _exit_if_action_mismatch(AlgorithmStepType.DATA_EXTRACTION)

        connection_details = {}

        # At least need the URI and type needs to be provided by the node
        uri = get_env_var(ContainerEnvNames.DATABASE_URI.value, mock_uri)
        type_ = get_env_var(ContainerEnvNames.DATABASE_TYPE.value, mock_type)
        if not uri:
            error("No database URI provided. Exiting...")
            exit(1)
        if not type_:
            error("No database type provided. Exiting...")
            exit(1)

        connection_details["uri"] = uri
        connection_details["type"] = type_

        # Get the other details
        for key in os.environ:
            if key.startswith(ContainerEnvNames.DB_PARAM_PREFIX.value):
                connection_details[
                    key.replace(ContainerEnvNames.DB_PARAM_PREFIX.value, "")
                ] = os.environ[key]

        result = func(connection_details, *args, **kwargs)

        return _convert_to_parquet(result)

    wrapper.vantage6_decorator_step_type = AlgorithmStepType.DATA_EXTRACTION
    return wrapper


def preprocessing(func: callable) -> callable:
    """Decorator for pre-processing functions."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        # Validate that the correct action is invoked in combination with the function
        # that is wrapped by this decorator.
        _exit_if_action_mismatch(AlgorithmStepType.PREPROCESSING)

        result = func(*args, **kwargs)

        return _convert_to_parquet(result)

    wrapper.vantage6_decorator_step_type = AlgorithmStepType.PREPROCESSING
    return wrapper


def federated(func: callable) -> callable:
    """Decorator for federated functions."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        _exit_if_action_mismatch(AlgorithmStepType.FEDERATED_COMPUTE)
        result = func(*args, **kwargs)
        return result

    wrapper.vantage6_decorator_step_type = AlgorithmStepType.FEDERATED_COMPUTE
    return wrapper


def central(func: callable) -> callable:
    """Decorator for central functions."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        _exit_if_action_mismatch(AlgorithmStepType.CENTRAL_COMPUTE)
        result = func(*args, **kwargs)
        return result

    wrapper.vantage6_decorator_step_type = AlgorithmStepType.CENTRAL_COMPUTE
    return wrapper
