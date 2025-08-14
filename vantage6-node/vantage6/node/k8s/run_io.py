# This up-front import of concurrent.futures.thread prevents the issue described on
# https://github.com/vantage6/vantage6/issues/1950 which happens when pyarrow is unable
# to lazy-loading concurrent.futures.thread
# TODO This is a provisional solution, as this (random, difficult to reproduce) error
# requires further exploration
# pylint: disable=unused-import
import concurrent.futures.thread  # noqa: F401
import logging
import os
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from vantage6.common import logger_name
from vantage6.common.client.node_client import NodeClient
from vantage6.common.enum import AlgorithmStepType, RunStatus

from vantage6.node.globals import TASK_FILES_ROOT
from vantage6.node.k8s.session_manager import SessionFileManager


class RunIO:
    def __init__(
        self,
        run_id: int,
        session_id: int,
        action: AlgorithmStepType,
        client: NodeClient,
        dataframe_details: dict = None,
        task_dir_extension: str = None,
    ):
        """
        Responsible for the IO files between the node and the algorithm.

        Parameters
        ----------
        run_id: int
            ID of the run
        session_id: int
            ID of the session
        action: AlgorithmStepType
            Type of action that is being performed
        client: NodeClient
            Client to communicate with the server
        dataframe_details: dict, optional
            Details of the dataframe that is being used in the run. Required for
            actions that update the session state.
        task_dir_extension: str, optional
            Extension to the directory to put the run files in. This is used to prevent
            that nodes use the same task directory in a development environment.
            Defaults to None.
        """

        self.log = logging.getLogger(logger_name(__name__))
        self.run_id = run_id
        self.session_id = session_id
        self.session_file_manager = SessionFileManager(session_id, task_dir_extension)
        self.session_name = self.session_file_manager.session_name
        self.action = action
        self.df_name = dataframe_details.get("name") if dataframe_details else None
        self.df_id = dataframe_details.get("id") if dataframe_details else None
        self.db_label = dataframe_details.get("db_label") if dataframe_details else None
        self.client = client

        # This run needs its own directory to store the IO files
        if task_dir_extension:
            self.run_folder = os.path.join(
                TASK_FILES_ROOT, task_dir_extension, str(self.run_id)
            )
        else:
            self.run_folder = os.path.join(TASK_FILES_ROOT, str(self.run_id))

    @classmethod
    def from_dict(cls, data: dict, client: NodeClient, task_dir_extension: str = None):
        # TODO validate that the keys are present
        return cls(
            run_id=int(data["run_id"]),
            session_id=int(data["session_id"]),
            action=AlgorithmStepType(data["action"]),
            dataframe_details={
                "name": data.get("df_name"),
                "id": data.get("df_id"),
                "db_label": data.get("df_label"),
            },
            client=client,
            task_dir_extension=task_dir_extension,
        )

    @property
    def input_volume_name(self) -> str:
        return f"run-{self.run_id}-input"

    @property
    def token_volume_name(self) -> str:
        return f"run-{self.run_id}-token"

    @property
    def output_volume_name(self) -> str:
        return f"run-{self.run_id}-output"

    @property
    def container_name(self) -> str:
        return f"run-{self.run_id}"

    @property
    def output_file(self) -> str:
        return os.path.join(self.run_folder, "output")

    def create_files(self, input_, output_) -> tuple[str, str]:
        """
        Create the input and output files for the run.

        Parameters
        ----------
        input: bytes
            Content of the input file
        output: bytes
            Content of the output file

        Returns
        -------
        tuple[str, str, str]
            Paths to the input, output and token files
        """
        return (
            self._create_run_io_file("input", input_),
            self._create_run_io_file("output", output_),
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

        Returns
        -------
        str
            Path to the created file
        """
        self.log.debug("Creating file %s for run %s", filename, self.run_id)

        relative_path = Path(str(self.run_id)) / filename
        file_path = Path(self.run_folder) / filename

        file_dir = Path(file_path).parent
        file_dir.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as file_:
            file_.write(content)

        return str(relative_path)

    def process_output(self) -> tuple[bytes, RunStatus]:
        """
        Read the output file of the run.

        Returns
        -------
        bytes
            Content of the output file
        """

        if self.action in [
            AlgorithmStepType.DATA_EXTRACTION,
            AlgorithmStepType.PREPROCESSING,
        ]:
            try:
                table = pq.read_table(self.output_file)
            except Exception as e:
                self.log.exception(
                    "Error reading output file for run ID %s, session ID %s, action %s."
                    " Exception: %s",
                    self.run_id,
                    self.session_id,
                    self.action,
                    str(e),
                )
                return b"", RunStatus.UNEXPECTED_OUTPUT

            # no algorithm result, but update the session files
            return b"", self._update_session(table)

        elif AlgorithmStepType.is_compute(self.action):
            with open(self.output_file, "rb") as fp:
                result = fp.read()

            # update the session state that compute run has been completed
            self.session_file_manager.update_state_file(
                action=self.action.value,
                message="Algorithm completed successfully.",
            )
            return result, RunStatus.COMPLETED
        else:
            self.log.error("Unknown action: %s", self.action)
            return b"", RunStatus.UNKNOWN_ERROR

    def _update_session(self, algo_result: pa.Table) -> RunStatus:
        """
        Update the session state with the results of the algorithm.

        Parameters
        ----------
        algo_result: pa.Table
            Table with the results of the algorithm

        Returns
        -------
        RunStatus
            Status of the run
        """
        if not self.df_name:
            self.log.error(
                "A session task was started without a dataframe. The session ID "
                "is %s and the run ID is %s.",
                self.session_id,
                self.run_id,
            )
            return RunStatus.FAILED

        self.log.debug(
            "Updating session %s for df %s.",
            self.session_id,
            self.df_name,
        )

        try:
            self.session_file_manager.write_dataframe_file(algo_result, self.df_name)
        except Exception:
            self.log.exception("Error writing data frame to parquet file")
            return RunStatus.FAILED

        self.session_file_manager.update_state_file(
            action=self.action.value,
            message="Session updated.",
            filename=f"{self.df_name}.parquet",
            df_name=self.df_name,
        )

        # Each node reports the column names for this dataframe in the session. In the
        # horizontal case all the nodes should report the same column names.
        columns_info = [
            {"name": field.name, "dtype": str(field.type)}
            for field in algo_result.schema
        ]
        self.client.column.post(self.df_id, columns_info)
        self.log.debug("Column data sent to server: %s", columns_info)
        return RunStatus.COMPLETED
