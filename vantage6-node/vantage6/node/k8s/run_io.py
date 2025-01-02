import logging
import datetime
import os

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from vantage6.node.globals import TASK_FILES_ROOT


class RunIO:

    def __init__(
        self, run_id: int, session_id: int, host_data_dir: str = TASK_FILES_ROOT
    ):

        self.logger = logging.getLogger(__name__)
        self.run_id = run_id
        self.session_id = session_id

        # The directory where the data is stored
        self.dir = host_data_dir

        # This run needs its own directory to store the IO files
        self.run_folder = os.path.join(self.dir, self.run_id)

        # A session folder is used to store the dataframes that are shared between
        # the runs. It also contains the session state file.
        self.session_name = f"session_{self.session_id:09d}"
        self.session_state_file_name = "session_state.parquet"

        self.session_folder = os.path.join(self.dir, "sessions", self.session_name)
        os.mkdir(self.session_folder, exist_ok=True)
        self.session_state_file = os.path.join(
            self.session_folder, self.session_state_file_name
        )

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
        file_path = os.path.join(self.dir, self.run_id, filename)
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
                "timestamp": [datetime.now()],
                "message": ["Created this session file."],
                "dataframe": [""],
            }
        )
        pq.write_table(session_state, self.session_state_file)

    @property
    def input_volume_name(self) -> str:
        return f"task_{self.run_id}_input"

    @property
    def output_volume_name(self) -> str:
        return f"task_{self.run_id}_output"

    @property
    def session_volume_name(self) -> str:
        return self.session_name
