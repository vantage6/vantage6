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


# TODO this function updates the session which is usually done in an algorithm run.
# Since this is just removing a dataframe, that doesn't work, but the code should be
# refactored to add this in a better place
def delete_dataframe(df_name: str, session_id: str) -> None:
    """
    Delete a dataframe from the node.

    Parameters
    ----------
    df_name: str
        Name of the dataframe to delete
    session_id: str
        ID of the session to delete the dataframe from
    """
    log.info(f"Deleting dataframe file '%s'", df_name)

    # Get the path to the dataframe file
    df_path = (
        Path(TASK_FILES_ROOT)
        / "sessions"
        / f"session{session_id:09d}"
        / f"{df_name}.parquet"
    )

    # Check if the file exists
    if not df_path.exists():
        log.warning(f"Dataframe file '%s' does not exist", df_path)
        return

    # Delete the file
    df_path.unlink()
    log.info(f"Dataframe file '%s' deleted", df_path)

    # update session state
    session_state_file = df_path.parent / "session_state.parquet"
    session_state = pd.read_parquet(session_state_file)
    new_row = pd.DataFrame(
        [
            {
                "action": "delete",
                "file": f"{df_name}.parquet",
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "message": "Dataframe deleted",
                "dataframe": df_name,
            }
        ]
    )
    session_state = pd.concat([session_state, new_row], ignore_index=True)
    try:
        session_state_table = pa.Table.from_pandas(session_state)
        pq.write_table(session_state_table, session_state_file)
    except Exception:
        log.exception("Error writing session state to parquet file")
