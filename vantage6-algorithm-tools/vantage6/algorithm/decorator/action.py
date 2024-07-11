import os
import pyarrow as pa
import pandas as pd

from datetime import datetime
from functools import wraps

from vantage6.common import error, debug
from vantage6.common.enums import LocalAction
from vantage6.algorithm.tools.exceptions import DataTypeError, SessionError


def data_extraction(func: callable) -> callable:
    # v Verify that the container has been started as data_extraction
    # v Store return DataFrame in a parquet file
    # v Write some other status statement in the output
    # v Update session log
    # - report column names and types to the server
    @wraps(func)
    def wrapper(*args, **kwargs) -> None:
        exit_if_action_mismatch(LocalAction.DATA_EXTRACTION)

        result = func(*args, **kwargs)

        debug("Verifying returned data type from the data extraction step.")
        if not isinstance(result, pd.DataFrame):
            raise DataTypeError(
                "Data extraction function did not return a Pandas DataFrame."
            )

        # TODO give a sensible name to the parquet file
        debug("Writing data to parquet file.")
        try:
            pa.Table.from_pandas(result).write_table("data_extraction_result.parquet")
        except Exception as e:
            error(f"Error writing data to parquet file: {e}")
            raise

        _raise_if_session_already_exists()
        _create_session_state_file()

        _set_state(
            "data-extraction",
            "data_extraction_result.parquet",
            "Data extraction complete.",
        )

        # TODO report column names
        # TODO report the column types
        # obtain token
        # create algorithm client
        # post to the session endpoint

        # Nothing is returned from the data-extraction container to the vantage6 server
        return

    return wrapper


def _set_state(action: str, file: str, message: str):
    debug("Updating session state.")
    try:
        state = pa.parquet.read_table("session_state.parquet").to_pandas()
        state = state.append(
            {
                "step": "data-extraction",
                "action": action,
                "file": file,
                "timestamp": datetime.now(),
                "message": message,
            },
            ignore_index=True,
        )
        pa.Table.from_pandas(state).write_table("session_state.parquet")
    except Exception as e:
        error(f"Error when updating session state: {e}")
        raise SessionError("Error when updating session state.")


def _create_session_state_file():
    debug("Creating local session file.")
    try:
        pa.Table.from_pandas(
            pd.DataFrame(columns=["step", "action", "file", "timestamp", "message"])
        ).write_table("session_state.parquet")
    except Exception as e:
        error(f"Error when creating local session file.")
        raise SessionError("Error when creating local session file.")


def _raise_if_session_already_exists():
    if os.path.exists("session_state.parquet"):
        debug(
            "Session state file already exists. Which should not be the case as the "
            "data extraction step is the first step in the workflow. Exiting."
        )
        raise SessionError("Session state file already exists.")


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
    debug("Verifying container action.")
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
