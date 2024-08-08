# TODO the task folder is also created by this class. This folder needs
# to be cleaned at some point.
import logging
import os
import docker.errors
import json
import base64
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from datetime import datetime
from pathlib import Path

from docker import DockerClient

from vantage6.common.globals import APPNAME, ENV_VAR_EQUALS_REPLACEMENT, STRING_ENCODING
from vantage6.common.docker.addons import (
    remove_container_if_exists,
    remove_container,
    running_in_docker,
)
from vantage6.common.docker.network_manager import NetworkManager
from vantage6.common.enum import RunStatus, LocalAction
from vantage6.node import NodeClient
from vantage6.node.util import get_parent_id
from vantage6.node.globals import ALPINE_IMAGE, ENV_VARS_NOT_SETTABLE_BY_NODE
from vantage6.node.docker.vpn_manager import VPNManager
from vantage6.node.docker.squid import Squid
from vantage6.node.docker.docker_base import DockerBaseManager
from vantage6.node.docker.exceptions import (
    UnknownAlgorithmStartFail,
    PermanentAlgorithmStartFail,
    AlgorithmContainerNotFound,
    DataFrameNotFound,
)


class DockerTaskManager(DockerBaseManager):
    """
    Manager for running a vantage6 algorithm container within docker.

    Ensures that the environment is properly set up (docker volumes,
    directories, environment variables, etc). Then runs the algorithm as a
    docker container. Finally, it monitors the container state and can return
    it's results when the algorithm finished.
    """

    def __init__(
        self,
        image: str,
        docker_client: DockerClient,
        client: NodeClient,
        vpn_manager: VPNManager,
        node_name: str,
        run_id: int,
        task_info: dict,
        tasks_dir: Path,
        action: LocalAction,
        isolated_network_mgr: NetworkManager,
        databases: dict,
        docker_volume_name: str,
        session_id: int,
        alpine_image: str | None = None,
        proxy: Squid | None = None,
        device_requests: list | None = None,
        requires_pull: bool = False,
    ):
        """
        Initialization creates DockerTaskManager instance

        Parameters
        ----------
        image: str
            Name of docker image to be run
        docker_client: DockerClient
            Docker client instance to use
        client: NodeClient
            Node client in order to communicate with the vantage6 server
        vpn_manager: VPNManager
            VPN manager required to set up traffic forwarding via VPN
        node_name: str
            Name of the node, to track running algorithms
        run_id: int
            Algorithm run identifier
        task_info: dict
            Dictionary with info about the task
        tasks_dir: Path
            Directory in which this task's data are stored
        action: LocalAction
            Action to be performed by the container
        isolated_network_mgr: NetworkManager
            Manager of isolated network to which algorithm needs to connect
        databases: dict
            List of databases
        docker_volume_name: str
            Name of the docker volume
        session_vol_name: str
            Name of the session docker volume
        session_id: int
            Session ID
        alpine_image: str | None
            Name of alternative Alpine image to be used
        device_requests: list | None
            List of DeviceRequest objects to be passed to the algorithm
            container
        requires_pull: bool
            If true, and the Docker image cannot be pulled, don't start the algorithm
            event if a local image is available
        """
        self.task_id = task_info["id"]
        self.log = logging.getLogger(f"task_manager {self.task_id}|{session_id}")

        super().__init__(isolated_network_mgr, docker_client=docker_client)
        self.client = client
        self.image = image
        self.__vpn_manager = vpn_manager
        self.run_id = run_id
        self.session_id = session_id
        self.task_id = task_info["id"]
        self.action = action
        self.parent_id = get_parent_id(task_info)
        self.__tasks_dir = tasks_dir
        self.databases = databases
        self.data_volume_name = docker_volume_name
        self.node_name = node_name
        self.alpine_image = ALPINE_IMAGE if alpine_image is None else alpine_image
        self.proxy = proxy
        self.requires_pull = requires_pull

        if task_info.get("dataframe"):
            self.dataframe_handle = task_info["dataframe"].get("handle", None)

        print(session_id)
        self.container = None
        self.status_code = None
        self.docker_input = None

        self.labels = {
            f"{APPNAME}-type": "algorithm",
            "node": node_name,
            "run_id": str(run_id),
        }
        self.helper_labels = self.labels.copy()
        self.helper_labels[f"{APPNAME}-type"] = "algorithm-helper"

        # FIXME: these values should be retrieved from DockerNodeContext
        #   in some way.
        self.data_folder = "/mnt/data"
        self.session_folder = "/mnt/session"
        self.session_state_file_name = "state.parquet"
        # FIXME: this `tmp_folder` might be used by some algorithms.In v5+ the
        # `TEMPORARY_FOLDER` environment variable should be removed and all these
        # algorithms should be updated to use the `SESSION_FOLDER` environment variable.
        self.tmp_folder = "/mnt/tmp"

        # keep track of the task status
        self.status: RunStatus = RunStatus.INITIALIZING

        # Set device requests
        self.device_requests = []
        if device_requests:
            self.device_requests = device_requests

    def is_finished(self) -> bool:
        """
        Checks if algorithm container is finished

        Returns
        -------
        bool:
            True if algorithm container is finished
        """
        try:
            self.container.reload()
        except (docker.errors.NotFound, AttributeError):
            self.log.error("Container not found")
            self.log.error("- task id: %s", self.task_id)
            self.log.error("- result id: %s", self.task_id)
            self.status = RunStatus.UNKNOWN_ERROR
            raise AlgorithmContainerNotFound()

        return self.container.status == "exited"

    def report_status(self) -> str:
        """
        Checks if algorithm has exited successfully. If not, it prints an
        error message

        Returns
        -------
        logs: str
            Log messages of the algorithm container
        """
        logs = self.container.logs().decode("utf8")

        # report if the container has a different status than 0
        self.status_code = self.container.attrs["State"]["ExitCode"]
        if self.status_code:
            self.log.error(f"Received non-zero exitcode: {self.status_code}")
            self.log.error(f"  Container id: {self.container.id}")
            self.log.info(logs)
            self.status = RunStatus.CRASHED
        else:
            self.status = RunStatus.COMPLETED
        return logs

    def get_results(self) -> bytes:
        """
        If the action is to compute, read results output file of the algorithm
        container. Otherwise, return an empty byte string.

        Returns
        -------
        bytes:
            Results of the algorithm container
        """

        match self.action:

            case LocalAction.DATA_EXTRACTION | LocalAction.PREPROCESSING:

                try:
                    result = pq.read_table(self.output_file)
                except Exception:
                    self.log.exception("Error reading output file")
                    self.status = RunStatus.UNEXPECTED_OUTPUT
                    return b""

                self._update_session(result)
                return b""

            case LocalAction.COMPUTE:

                with open(self.output_file, "rb") as fp:
                    result = fp.read()

                self._update_session_state(
                    LocalAction.COMPUTE.value,
                    "no file",
                    f"Algorithm from '{self.image}' completed successfully.",
                )
                return result

            case _:

                self.log.error("Unknown action: %s", self.action)
                self.status = RunStatus.UNKNOWN_ERROR
                return b""

    def _update_session(self, table: pa.Table) -> None:
        """
        Update the session dataframe with the results of the algorithm

        Parameters
        ----------
        table: pa.Table
            Table with the results of the algorithm
        """

        self.log.debug(
            f"Updating session {self.session_id} for handle {self.dataframe_handle}."
        )

        if not self.dataframe_handle:
            self.log.error("No dataframe handle found.")
            self.log.debug(
                "A session task is started but had no dataframe handle. The session ID "
                f"is {self.session_id} and the task ID is {self.task_id}.",
            )
            self.status = RunStatus.FAILED
            return

        try:
            # Overwrite the session table
            pq.write_table(
                table,
                os.path.join(
                    self.session_folder_path, f"{self.dataframe_handle}.parquet"
                ),
            )
        except Exception:
            self.log.exception(f"Error writing status to state parquet file")
            self.status = RunStatus.FAILED
            return

        self._update_session_state(
            self.action,
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
            f"/session/{self.session_id}/dataframe/{self.dataframe_handle}",
            method="patch",
            json=columns_info,
        )
        self.log.debug(f"Columns info sent to server: {columns_info}")

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
                    "timestamp": datetime.now(),
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
            self.log.exception("Error writing session data to parquet file")

        return

    def pull(self, local_exists: bool) -> None:
        """
        Pull the latest docker image.

        Parameters
        ----------
        local_exists: bool
            Whether the image already exists locally

        Raises
        ------
        PermanentAlgorithmStartFail
            If the image could not be pulled and does not exist locally
        """
        try:
            self.log.info("Retrieving latest image: '%s'", self.image)
            self.docker.images.pull(self.image)
        except Exception as exc:
            if isinstance(exc, docker.errors.APIError):
                self.log.warning("Failed to pull image! Image does not exist")
            else:
                self.log.warning("Failed to pull image!")
            if not local_exists:
                self.log.exception(exc)
                self.status = RunStatus.NO_DOCKER_IMAGE
                raise PermanentAlgorithmStartFail from exc
            elif self.requires_pull:
                self.log.warning(
                    "Node policy prevents local image to be used to start algorithm"
                )
                self.status = RunStatus.NO_DOCKER_IMAGE
                raise PermanentAlgorithmStartFail from exc
            else:
                self.log.info("Using local image")

    def run(
        self,
        docker_input: bytes,
        token: str | None,
        algorithm_env: dict,
        databases_to_use: list[str],
    ) -> list[dict] | None:
        """
        Runs the docker-image in detached mode.

        It will will attach all mounts (input, output and datafile) to the
        docker image. And will supply some environment variables.

        Parameters
        ----------
        docker_input: bytes
            Input that can be read by docker container
        token: str | None
            Bearer token that the container can use to authenticate with the server
        algorithm_env: dict
            Dictionary with additional environment variables to set
        databases_to_use: list[str]
            List of labels of databases to use in the task

        Returns
        -------
        list[dict] | None
            Description of each port on the VPN client that forwards traffic to
            the algo container. None if VPN is not set up.
        """
        # generate task folders
        self._make_task_folders()

        # prepare volumes
        self.docker_input = docker_input
        self.volumes = self._prepare_volumes(token)
        self.log.debug("volumes: %s", self.volumes)

        # setup environment variables
        self.environment_variables = self._setup_environment_vars(
            algorithm_env=algorithm_env, databases_to_use=databases_to_use
        )

        # run the algorithm as docker container
        vpn_ports = self._run_algorithm()
        return vpn_ports

    def cleanup(self) -> None:
        """Cleanup the containers generated for this task"""
        remove_container(self.helper_container, kill=True)
        remove_container(self.container, kill=True)

    def _run_algorithm(self) -> list[dict] | None:
        """
        Run the algorithm container

        Start up a helper container to complete VPN setup, pull the latest
        image and then run the algorithm

        Returns
        -------
        list[dict] or None
            Description of each port on the VPN client that forwards traffic to
            the algo container. None if VPN is inactive
        """
        vpn_ports = None
        container_name = f"{APPNAME}-{self.node_name}-run-{self.run_id}"
        helper_container_name = container_name + "-helper"

        # Try to pull the latest image
        local_exists = len(self.docker.images.list(name=self.image)) > 0
        self.pull(local_exists=local_exists)

        # remove algorithm containers if they were already running
        self.log.debug("Check if algorithm container is already running")
        remove_container_if_exists(docker_client=self.docker, name=container_name)
        remove_container_if_exists(
            docker_client=self.docker, name=helper_container_name
        )

        if self.__vpn_manager:
            # if VPN is active, network exceptions must be configured
            # First, start a container that runs indefinitely. The algorithm
            # container will run in the same network and network exceptions
            # will therefore also affect the algorithm.
            self.log.debug("Start helper container to setup VPN network")
            self.helper_container = self.docker.containers.run(
                command="sleep infinity",
                image=self.alpine_image,
                labels=self.helper_labels,
                network=self.isolated_network_mgr.network_name,
                name=helper_container_name,
                detach=True,
            )
            # setup forwarding of traffic via VPN client to and from the
            # algorithm container:
            self.log.debug("Setup port forwarder")
            vpn_ports = self.__vpn_manager.forward_vpn_traffic(
                helper_container=self.helper_container, algo_image_name=self.image
            )

        # try reading docker input
        # FIXME BvB 2023-02-03: why do we read docker input here? It is never
        # really used below. Should it?
        deserialized_input = None
        if self.docker_input:
            self.log.debug("Deserialize input")
            try:
                deserialized_input = json.loads(self.docker_input)
            except Exception:
                pass

        # attempt to run the image
        try:
            if deserialized_input:
                self.log.info(
                    f"Run docker image {self.image} with input "
                    f"{self._printable_input(deserialized_input)}"
                )
            else:
                self.log.info(f"Run docker image {self.image}")
            self.container = self.docker.containers.run(
                self.image,
                detach=True,
                environment=self.environment_variables,
                network="container:" + self.helper_container.id,
                volumes=self.volumes,
                name=container_name,
                labels=self.labels,
                device_requests=self.device_requests,
            )

        except Exception as e:
            self.status = RunStatus.START_FAILED
            raise UnknownAlgorithmStartFail(e)

        self.status = RunStatus.ACTIVE
        return vpn_ports

    @staticmethod
    def _printable_input(input_: str | dict) -> str:
        """
        Return a version of the input with limited number of characters

        Parameters
        ----------
        input: str | dict
            Deserialized input of a task

        Returns
        -------
        str
            Input with limited number of characters, to be printed to logs
        """
        if isinstance(input_, dict):
            input_ = str(input_)
        if len(input_) > 550:
            return f"{input_[:500]}... ({len(input_)-500} characters omitted)"
        return input_

    def _make_task_folders(self) -> None:
        """Generate task folders"""
        # FIXME: We should have a separate mount/volume for this. At the
        #   moment this is a potential leak as containers might access input,
        #   output and token from other containers.
        #
        #   This was not possible yet as mounting volumes from containers
        #   is terrible when working from windows (as you have to convert
        #   from windows to unix several times...).

        # If we're running in docker __tasks_dir will point to a location on
        # the data volume.
        # Alternatively, if we're not running in docker it should point to the
        # folder on the host that can act like a data volume. In both cases,
        # we can just copy the required files to it
        self.task_folder_name = f"task-{self.run_id:09d}"
        self.task_folder_path = os.path.join(self.__tasks_dir, self.task_folder_name)
        os.makedirs(self.task_folder_path, exist_ok=True)
        self.output_file = os.path.join(self.task_folder_path, "output")

        self.session_folder_name = f"session-{self.session_id:09d}"
        self.session_folder_path = os.path.join(
            self.__tasks_dir, self.session_folder_name
        )
        os.makedirs(self.session_folder_path, exist_ok=True)
        self.session_state_file = os.path.join(
            self.session_folder_path, self.session_state_file_name
        )

    def _prepare_volumes(self, token: str) -> dict:
        """
        The algorithm is provisioned with a session and data volume. The data
        folder is used for the IO interface with the node instance (e.g. to read the
        output from the algorithm). The session folder is used to intermediate data
        between subsequent steps in the algorithm (e.g. one container extracts the
        data and the next one actually computes statistics on this container).


        Parameters
        ----------
        token: str | None
            Bearer token that the container can use to authenticate with the server

        Returns
        -------
        dict:
            Volumes to support running the algorithm
        """
        if isinstance(self.docker_input, str):
            self.docker_input = self.docker_input.encode("utf8")

        # Create I/O files & token for the algorithm container
        self.log.debug("prepare IO files in docker volume")
        io_files = [
            ("input", self.docker_input),
            ("output", b""),
        ]

        if token:
            io_files.append(("token", token.encode("ascii")))

        for filename, data in io_files:
            filepath = os.path.join(self.task_folder_path, filename)

            with open(filepath, "wb") as fp:
                fp.write(data)

        if not os.path.exists(self.session_state_file):
            self.log.info("Create session state file")
            session_state = pa.table(
                {
                    "action": ["no action"],
                    "file": [self.session_state_file_name],
                    "timestamp": [datetime.now()],
                    "message": ["Created this session file."],
                    "dataframe": [""],
                }
            )
            pq.write_table(session_state, self.session_state_file)

        volumes = {}
        if running_in_docker():
            volumes[self.data_volume_name] = {"bind": self.data_folder, "mode": "rw"}
        else:
            volumes[self.__tasks_dir] = {"bind": self.data_folder, "mode": "rw"}
        return volumes

    def _setup_environment_vars(
        self, algorithm_env: dict, databases_to_use: list[str]
    ) -> dict:
        """ "
        Set environment variables required to run the algorithm

        Parameters
        ----------
        algorithm_env: dict
            Dictionary with additional environment variables to set
        databases_to_use: list[str]
            Labels of the databases to use

        Returns
        -------
        dict:
            Environment variables required to run algorithm
        """
        try:
            proxy_host = os.environ["PROXY_SERVER_HOST"]

        except Exception:
            self.log.warn("PROXY_SERVER_HOST not set, using host.docker.internal")
            self.log.debug("environment: %s", os.environ)
            proxy_host = "host.docker.internal"

        # define environment variables for the docker-container, the
        # host, port and api_path are from the local proxy server to
        # facilitate indirect communication with the central server
        # FIXME: we should only prepend data_folder if database_uri is a
        #   filename
        environment_variables = {
            "INPUT_FILE": f"{self.data_folder}/{self.task_folder_name}/input",
            "OUTPUT_FILE": f"{self.data_folder}/{self.task_folder_name}/output",
            "SESSION_FOLDER": f"{self.data_folder}/{self.session_folder_name}",
            "SESSION_FILE": (
                f"{self.data_folder}/{self.session_folder_name}"
                f"/{self.session_state_file_name}"
            ),
            "HOST": f"http://{proxy_host}",
            "PORT": os.environ.get("PROXY_SERVER_PORT", 8080),
            "API_PATH": "",
            "FUNCTION_ACTION": self.action.value,
        }

        if self.action == LocalAction.COMPUTE:
            environment_variables["TOKEN_FILE"] = (
                f"{self.data_folder}/{self.task_folder_name}/token"
            )

        # Add squid proxy environment variables
        if self.proxy:
            # applications/libraries in the algorithm container need to adhere
            # to the proxy settings. Because we are not sure which application
            # is used for the request we both set HTTP_PROXY and http_proxy and
            # HTTPS_PROXY and https_proxy for the secure connection.
            environment_variables["HTTP_PROXY"] = self.proxy.address
            environment_variables["http_proxy"] = self.proxy.address
            environment_variables["HTTPS_PROXY"] = self.proxy.address
            environment_variables["https_proxy"] = self.proxy.address

            no_proxy = []
            if self.__vpn_manager.subnet:
                # Computing all ips in the vpn network is not feasible as the
                # no_proxy environment variable will be too long for the
                # container to start. So we only add the net + mask. For some
                # applications and libraries this is format is ignored.
                no_proxy.append(self.__vpn_manager.subnet)
            no_proxy.append("localhost")
            no_proxy.append(proxy_host)

            # Add the NO_PROXY and no_proxy environment variable.
            environment_variables["NO_PROXY"] = ", ".join(no_proxy)
            environment_variables["no_proxy"] = ", ".join(no_proxy)

        # Only the data extraction step can access the source databases
        if self.action == LocalAction.DATA_EXTRACTION:
            # TODO
            # 1. Check that the database type is source
            # 2. Check that only one database has been requested
            # 3. Pass the database URI to the algorithm
            failed = False
            if len(databases_to_use) > 1:
                self.log.error(
                    "Only one database can be used in the data extraction step."
                )
                failed = True

            source_database = databases_to_use[0]

            if source_database["type"] != "source":
                self.log.error(
                    "The database used in the data extraction step must be of type "
                    "'source'."
                )
                failed = True

            if source_database["label"] not in self.databases:
                self.log.error(
                    "The database used in the data extraction step does not exist."
                )
                failed = True

            if failed:
                self.status = RunStatus.FAILED
                raise PermanentAlgorithmStartFail()

            db = self.databases[source_database["label"]]

            environment_variables["DATABASE_URI"] = (
                f"{self.data_folder}/{os.path.basename(db['uri'])}"
                if db["is_file"]
                else db["uri"]
            )

            environment_variables["DATABASE_TYPE"] = db["type"]

            # variables.
            if "env" in db:
                for key in db["env"]:
                    env_key = f"DB_PARAM_{key.upper()}"
                    environment_variables[env_key] = db["env"][key]

        # In the other case we are dealing with a dataframe in a session
        else:

            if not all(df["type"] == "handle" for df in databases_to_use):
                self.log.error(
                    "All databases used in the algorithm must be of type 'handle'."
                )
                self.status = RunStatus.FAILED
                raise PermanentAlgorithmStartFail()

            # Validate that the requested handles exists. At this point they need to as
            # we are about to start the task.
            requested_handles = {db["label"] for db in databases_to_use}
            available_handles = {
                file_.stem for file_ in Path(self.session_folder_path).glob("*.parquet")
            }
            # check that requested handles is a subset of available handles
            if not requested_handles.issubset(available_handles):
                self.log.error(
                    "Requested dataframe handle(s) not found in session folder."
                )
                self.log.debug(f"Requested dataframe handles: {requested_handles}")
                self.log.debug(f"Available dataframe handles: {available_handles}")
                self.status = RunStatus.DATAFRAME_NOT_FOUND
                raise DataFrameNotFound(f"user requested {requested_handles}")

            environment_variables["USER_REQUESTED_DATAFRAME_HANDLES"] = ",".join(
                [db["label"] for db in databases_to_use]
            )

        # Load additional environment variables
        if algorithm_env:
            environment_variables = {**environment_variables, **algorithm_env}
            self.log.info("Custom environment variables are loaded!")
            self.log.debug(f"custom environment: {algorithm_env}")

        # validate whether environment variables don't contain any illegal
        # characters
        self._validate_environment_variables(environment_variables)

        # print the environment before encoding it so that the user can see
        # what is passed to the container
        self.log.debug(f"environment: {environment_variables}")

        # encode environment variables to prevent special characters from being
        # possibly code injection
        environment_variables = self._encode_environment_variables(
            environment_variables
        )

        return environment_variables

    def _validate_environment_variables(self, environment_variables: dict) -> None:
        """
        Check whether environment variables don't contain any illegal
        characters

        Parameters
        ----------
        environment_variables: dict
            Environment variables required to run algorithm

        Raises
        ------
        PermanentAlgorithmStartFail
            If environment variables contain illegal characters
        """
        msg = None
        for key in environment_variables:
            if not key.isidentifier():
                msg = (
                    f"Environment variable '{key}' is invalid: environment "
                    " variable names should only contain number, letters and "
                    " underscores, and start with a letter."
                )
            elif key in ENV_VARS_NOT_SETTABLE_BY_NODE:
                msg = (
                    f"Environment variable '{key}' cannot be set: this "
                    "variable is set in the algorithm Dockerfile and cannot "
                    "be overwritten."
                )
            if msg:
                self.status = RunStatus.FAILED
                self.log.error(msg)
                raise PermanentAlgorithmStartFail(msg)

    def _encode_environment_variables(self, environment_variables: dict) -> dict:
        """
        Encode environment variable values to ensure that special characters
        are not interpretable as code while transferring them to the algorithm
        container.

        Parameters
        ----------
        environment_variables: dict
            Environment variables required to run algorithm

        Returns
        -------
        dict:
            Environment variables with encoded values
        """

        def _encode(string: str) -> str:
            """Encode env var value

            We first encode to bytes, then to b32 and then decode to a string.
            Finally, '=' is replaced by less sensitve characters to prevent
            issues with interpreting the encoded string in the env var value.

            Parameters
            ----------
            string: str
                String to be encoded

            Returns
            -------
            str:
                Encoded string

            Examples
            --------
            >>> _encode("abc")
            'MFRGG!!!'
            """
            return (
                base64.b32encode(string.encode(STRING_ENCODING))
                .decode(STRING_ENCODING)
                .replace("=", ENV_VAR_EQUALS_REPLACEMENT)
            )

        self.log.debug("Encoding environment variables")

        encoded_environment_variables = {}
        for key, val in environment_variables.items():
            encoded_environment_variables[key] = _encode(str(val))
        return encoded_environment_variables
