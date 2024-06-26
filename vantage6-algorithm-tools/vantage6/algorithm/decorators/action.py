import os
import pyarrow as pa
import pandas as pd

from functools import wraps

from vantage6.common import error, debug
from vantage6.common.enums import LocalAction
from vantage6.algorithm.tools.exceptions import DataTypeError, SessionError


def data_extraction(func: callable) -> callable:
    # v Verify that the container has been started as data_extraction
    # - Store return DataFrame in a parquet file
    # - Write some other status statement in the output
    # - Update session log
    @wraps(func)
    def wrapper(*args, **kwargs) -> None:
        debug("Verifying container action.")
        exit_if_action_mismatch(LocalAction.DATA_EXTRACTION)

        result = func(*args, **kwargs)

        debug("Verifying returned data type from the data extraction step.")
        if not isinstance(result, pd.DataFrame):
            raise DataTypeError(
                "Data extraction function did not return a Pandas DataFrame."
            )

        # TODO give a sensible name to the parquet file
        debug("Writing data to parquet file.")
        pa.Table.from_pandas(result).write_table("data.parquet")

        debug("Updating session state.")
        if _session_state_file_exists():
            debug(
                "Session state file already exists. Which should not be the case as the "
                "data extraction step is the first step in the workflow. Exiting."
            )
            raise SessionError("Session state file already exists.")
        _create_session_state_file()

        # TODO report column names at this point ?
        return

    return wrapper


def _create_session_state_file():
    pa.Table.from_pandas(
        pd.DataFrame(columns=["step", "action", "file", "timestamp", "message"])
    ).write_table("session_state.parquet")


def _session_state_file_exists():
    return os.path.exists("session_state.parquet")


def pre_processing(func: callable):
    # v Verify that the container has been started as pre_processing
    # - To store return dataframe in a parquet file
    # - Write some other status statement in the output
    # - Update the session log
    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        exit_if_action_mismatch(LocalAction.PREPROCESSING)
        result = func(*args, **kwargs)
        return result

    return wrapper


def federated(func: callable):
    # v Verify that the container has been started as federated
    # - Obtain the data from the session or from file based DB (wrapper)
    # - Update the session log
    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        exit_if_action_mismatch(LocalAction.COMPUTE)
        result = func(*args, **kwargs)
        return result

    return wrapper


def central(func: callable):
    # v Verify that the container has been started as central
    # - update the session log
    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        exit_if_action_mismatch(LocalAction.COMPUTE)
        result = func(*args, **kwargs)
        return result

    return wrapper


def exit_if_action_mismatch(requested_action: LocalAction):

    if "CONTAINER_ACTION" not in os.environ:
        error("Container action not set. Exiting.")
        exit(1)

    action = os.environ["CONTAINER_ACTION"]
    if action != requested_action:
        error(
            f"Container started as {action}, but user requested {requested_action}. "
            "Exiting."
        )
        exit(1)
