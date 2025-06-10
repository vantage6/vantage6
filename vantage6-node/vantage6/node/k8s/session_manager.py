import logging
import os
import datetime

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd

from vantage6.common import logger_name
from vantage6.node.globals import TASK_FILES_ROOT


class SessionFileManager:
    """
    Class to manage session state on the node.
    """

    def __init__(self, session_id: str):
        """
        Parameters
        ----------
        session_id: str
            ID of the session
        """
        self.log = logging.getLogger(logger_name(__name__))
        self.session_id = session_id

        self.session_name = f"session{self.session_id:09d}"
        self.session_state_file_name = "session_state.parquet"

        self.session_folder = os.path.join("sessions", self.session_name)
        self.local_session_folder = os.path.join(TASK_FILES_ROOT, self.session_folder)
        os.makedirs(self.local_session_folder, exist_ok=True)
        self.session_state_file = os.path.join(
            self.local_session_folder, self.session_state_file_name
        )

        if not Path(self.session_state_file).exists():
            self._create_session_state_file(self.session_id)

    def update_state_file(
        self, action: str, message: str, filename: str = "", df_name: str = ""
    ) -> None:
        """
        Update the session state file with the current action, file and message

        Parameters
        ----------
        action: str
            Action that was performed
        message: str
            Message to be added to the state file
        filename: str, optional
            File resulting from the action
        df_name: str, optional
            Dataframe name that was updated. Some actions on the session are not
            related to a specific dataframe, so this parameter is optional.
        """
        self.log.debug(
            "Update session state file for action '%s' on dataframe '%s' ",
            action,
            df_name,
        )
        state = pq.read_table(self.session_state_file).to_pandas()
        new_row = pd.DataFrame(
            [
                {
                    "action": action,
                    "file": filename,
                    "timestamp": datetime.datetime.now(),
                    "message": message,
                    "dataframe": df_name,
                }
            ]
        )
        state = pd.concat([state, new_row], ignore_index=True)

        try:
            session_table = pa.Table.from_pandas(state)
            pq.write_table(session_table, self.session_state_file)
        except Exception:
            self.log.exception("Error writing session state to parquet file")

    def write_dataframe_file(self, algo_result: pa.Table, df_name: str) -> None:
        """
        Write the session dataframe to a parquet file.

        Parameters
        ----------
        algo_result: pa.Table
            Table with the results of the algorithm
        df_name: str
            Name of the dataframe to update
        """
        pq.write_table(
            algo_result, os.path.join(self.local_session_folder, f"{df_name}.parquet")
        )

    def delete_dataframe_file(self, df_name: str) -> None:
        """
        Delete the session dataframe file.
        """
        df_path = Path(self.local_session_folder) / f"{df_name}.parquet"
        if not df_path.exists():
            self.log.warning("Dataframe file '%s' does not exist", df_path)
            return

        try:
            df_path.unlink()
            self.log.info("Dataframe file '%s' deleted", df_path)
        except Exception:
            self.log.exception("Error deleting dataframe file '%s'", df_path)

        # update session state to include the deletion
        self.update_state_file(
            action="delete",
            message="Dataframe deleted",
            filename=f"{df_name}.parquet",
            df_name=df_name,
        )

    def _create_session_state_file(self, session_id: int) -> str:
        """
        Create a file to store the state of the session.

        Parameters
        ----------
        session_id: int
            ID of the session

        Returns
        -------
        str
            Path to the session state file
        """
        self.log.debug(f"Creating session state file for session_id={session_id}")
        session_state = pa.table(
            {
                "action": [""],
                "file": [self.session_state_file_name],
                "timestamp": [datetime.datetime.now()],
                "message": ["Created this session file."],
                "dataframe": [""],
            }
        )
        pq.write_table(session_state, self.session_state_file)
