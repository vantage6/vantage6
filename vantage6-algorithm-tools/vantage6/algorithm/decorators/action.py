import os

from functools import wraps

from vantage6.common import error
from vantage6.common.enums import LocalAction


def data_extraction(func: callable):
    # v Verify that the container has been started as data_extraction
    # - Store return dataframe in a parquet file
    # - Write some other status statement in the output
    # - Update session log
    @wraps(func)
    def wrapper(*args, **kwargs) -> callable:
        exit_if_action_mismatch(LocalAction.DATA_EXTRACTION)
        result = func(*args, **kwargs)
        return result

    return wrapper


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
    action = os.environ["CONTAINER_ACTION"]
    if action != requested_action:
        error(
            f"Container started as {action}, but user requested {requested_action}. "
            "Exiting."
        )
        exit(1)
