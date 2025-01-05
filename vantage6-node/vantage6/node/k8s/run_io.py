import logging
import datetime
import os

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd

from vantage6.node.globals import TASK_FILES_ROOT
from vantage6.common.enum import RunStatus, AlgorithmStepType
from vantage6.common import logger_name
from vantage6.common.client.node_client import NodeClient


class RunIO:

    def __init__(
        self,
        run_id: int,
        session_id: int,
        action: AlgorithmStepType,
        client: NodeClient,
        dataframe_handle: str = None,
        host_data_dir: str = TASK_FILES_ROOT,
    ):
        """
        Responsible for the IO files between the node and the algorithm.
        """

        self.log = logging.getLogger(logger_name(__name__))
        self.run_id = run_id
        self.session_id = session_id
        self.action = action
        self.dataframe_handle = dataframe_handle
        self.client = client

        # The directory where the data is stored
        self.dir = host_data_dir

        # This run needs its own directory to store the IO files
        self.run_folder = os.path.join(self.dir, str(self.run_id))

        # A session folder is used to store the dataframes that are shared between
        # the runs. It also contains the session state file.
        self.session_name = f"session{self.session_id:09d}"
        self.session_state_file_name = "session_state.parquet"

        self.session_folder = os.path.join(self.dir, "sessions", self.session_name)
        os.makedirs(self.session_folder, exist_ok=True)
        self.session_state_file = os.path.join(
            self.session_folder, self.session_state_file_name
        )

        if not Path(self.session_state_file).exists():
            self._create_session_state_file(self.session_id)

    @classmethod
    def from_dict(
        cls, data: dict, client: NodeClient, host_data_dir: str = TASK_FILES_ROOT
    ):
        # TODO validate that the keys are present
        # TODO the host_data_dir should be passed as an argument
        return cls(
            run_id=int(data["run_id"]),
            session_id=int(data["session_id"]),
            action=AlgorithmStepType(data["action"]),
            dataframe_handle=data["dataframe_handle"],
            host_data_dir=host_data_dir,
            client=client,
        )

    @property
    def input_volume_name(self) -> str:
        return f"task-{self.run_id}-input"

    @property
    def token_volume_name(self) -> str:
        return f"token-{self.run_id}-input"

    @property
    def output_volume_name(self) -> str:
        return f"task-{self.run_id}-output"

    @property
    def session_volume_name(self) -> str:
        return self.session_name

    @property
    def container_name(self) -> str:
        return f"run-{self.run_id}"

    @property
    def output_file(self) -> str:
        return os.path.join(self.run_folder, "output")

    def create_files(self, input_, output, token) -> tuple[str, str, str]:
        """
        Create the input, output and token files for the run.

        Parameters
        ----------
        input: bytes
            Content of the input file
        output: bytes
            Content of the output file
        token: bytes
            Content of the token file

        Returns
        -------
        tuple[str, str, str]
            Paths to the input, output and token files
        """
        return (
            self._create_run_io_file("input", input_),
            self._create_run_io_file("output", output),
            self._create_run_io_file("token", token),
        )

    def _create_run_io_file(self, filename: str, content: bytes) -> str:
        """
        Create a file with the given content.

        Parameters
        ----------
        filename: str
            Path to the file that is going to be created
        content: bytes
            Content that is going to be written to the file
        """
        self.log.debug(f"Creating file {filename} for run {self.run_id}")
        file_path = os.path.join(self.dir, str(self.run_id), filename)
        file_dir = Path(file_path).parent
        file_dir.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as file_:
            file_.write(content)

        return file_path

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

    def process_output(self) -> tuple[bytes, RunStatus]:
        """
        Read the output file of the run.

        Returns
        -------
        bytes
            Content of the output file
        """
        self.log.debug(AlgorithmStepType.DATA_EXTRACTION)
        self.log.debug(self.action)

        self.log.debug(AlgorithmStepType.DATA_EXTRACTION == self.action)

        self.log.debug(type(self.action))
        self.log.debug(type(AlgorithmStepType.DATA_EXTRACTION))

        match self.action:

            case AlgorithmStepType.DATA_EXTRACTION | AlgorithmStepType.PREPROCESSING:

                try:
                    table = pq.read_table(self.output_file)
                except Exception:
                    self.log.exception("Error reading output file")
                    return b"", RunStatus.UNEXPECTED_OUTPUT

                return b"", self._update_session(table)

            case AlgorithmStepType.COMPUTE:

                with open(self.output_file, "rb") as fp:
                    result = fp.read()

                self._update_session_state(
                    AlgorithmStepType.COMPUTE.value,
                    None,
                    f"Algorithm from '{self.image}' completed successfully.",
                )
                return result, RunStatus.COMPLETED

            case _:

                self.log.error("Unknown action: %s", self.action)
                return b"", RunStatus.UNKNOWN_ERROR

    def _update_session(self, table: pa.Table) -> RunStatus:
        """
        Update the session dataframe with the results of the algorithm

        Parameters
        ----------
        table: pa.Table
            Table with the results of the algorithm

        Returns
        -------
        RunStatus
            Status of the run
        """
        self.log.debug(
            f"Updating session {self.session_id} for handle {self.dataframe_handle}."
        )

        if not self.dataframe_handle:
            self.log.error("No dataframe handle found.")
            self.log.debug(
                "A session task was started but had no dataframe handle. The session ID "
                f"is {self.session_id} and the task ID is {self.task_id}.",
            )
            return RunStatus.FAILED

        try:
            # Create or overwrite the parquet data frame with the algorithm result
            pq.write_table(
                table,
                os.path.join(self.session_folder, f"{self.dataframe_handle}.parquet"),
            )
        except Exception:
            self.log.exception("Error writing data frame to parquet file")
            return RunStatus.FAILED

        self._update_session_state(
            self.action.value,
            f"{self.dataframe_handle}.parquet",
            "Session updated.",
            self.dataframe_handle,
        )

        # Each node reports the column names for this dataframe in the session. In the
        # horizontal case all the nodes should report the same column names.
        columns_info = [
            {"name": field.name, "dtype": str(field.type)} for field in table.schema
        ]
        self.client.request(
            f"/session/{self.session_id}/dataframe/{self.dataframe_handle}/column",
            method="post",
            json=columns_info,
        )
        self.log.debug("Column data sent to server: %s", columns_info)
        return RunStatus.COMPLETED

    def _update_session_state(
        self, action: str, filename: str, message: str, dataframe: str = ""
    ) -> None:
        """
        Update the session state file with the current action, file and message

        Parameters
        ----------
        action: str
            Action that was performed
        filename: str
            File resulting from the action
        message: str
            Message to be added to the state file
        dataframe: str, optional
            Dataframe handle that was updated. Some actions on the session are not
            related to a specific dataframe, so this parameter is optional.
        """
        self.log.debug(
            "Update session state file for action '%s' on dataframe '%s' ",
            action,
            dataframe,
        )
        state = pq.read_table(self.session_state_file).to_pandas()
        new_row = pd.DataFrame(
            [
                {
                    "action": action,
                    "file": filename,
                    "timestamp": datetime.datetime.now(),
                    "message": message,
                    "dataframe": dataframe,
                }
            ]
        )
        state = pd.concat([state, new_row], ignore_index=True)

        try:
            session_table = pa.Table.from_pandas(state)
            pq.write_table(session_table, self.session_state_file)
        except Exception:
            self.log.exception("Error writing session state to parquet file")

        return
