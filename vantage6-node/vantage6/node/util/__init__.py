import logging
from pathlib import Path
import datetime

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from vantage6.common import logger_name
from vantage6.node.globals import TASK_FILES_ROOT

log = logging.getLogger(logger_name(__name__))


def get_parent_id(task_dict: dict) -> int | None:
    """
    Get a task's parent id from a JSON task dictionary

    Parameters
    ----------
    task_dict: Dict
        Dictionary with task information

    Returns
    -------
    parent_id: int | None
        Parent_id of the task
    """
    return (
        task_dict["parent"]["id"]
        if task_dict["parent"] and "id" in task_dict["parent"]
        else None
    )
