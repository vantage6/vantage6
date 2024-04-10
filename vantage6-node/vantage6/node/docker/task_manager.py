# TODO the task folder is also created by this class. This folder needs
# to be cleaned at some point.
import logging
import os
import docker.errors
import json
import base64

from pathlib import Path
from docker import DockerClient

from vantage6.common.globals import APPNAME, ENV_VAR_EQUALS_REPLACEMENT, STRING_ENCODING
from vantage6.common.docker.addons import (
    remove_container_if_exists,
    remove_container,
    running_in_docker,
)
from vantage6.common.docker.network_manager import NetworkManager
from vantage6.common.task_status import TaskStatus
from vantage6.node.util import get_parent_id
from vantage6.node.globals import ALPINE_IMAGE, ENV_VARS_NOT_SETTABLE_BY_NODE
from vantage6.node.docker.vpn_manager import VPNManager
from vantage6.node.docker.squid import Squid
from vantage6.node.docker.docker_base import DockerBaseManager
from vantage6.node.docker.exceptions import (
    UnknownAlgorithmStartFail,
    PermanentAlgorithmStartFail,
    AlgorithmContainerNotFound,
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
        vpn_manager: VPNManager,
        node_name: str,
        run_id: int,
        task_info: dict,
        tasks_dir: Path,
        isolated_network_mgr: NetworkManager,
        databases: dict,
        docker_volume_name: str,
        alpine_image: str | None = None,
        proxy: Squid | None = None,
        device_requests: list | None = None,
    ):
        """
        Initialization creates DockerTaskManager instance

        Parameters
        ----------
        image: str
            Name of docker image to be run
        docker_client: DockerClient
            Docker client instance to use
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
        isolated_network_mgr: NetworkManager
            Manager of isolated network to which algorithm needs to connect
        databases: dict
            List of databases
        docker_volume_name: str
            Name of the docker volume
        alpine_image: str | None
            Name of alternative Alpine image to be used
        device_requests: list | None
            List of DeviceRequest objects to be passed to the algorithm
            container
        """
        self.task_id = task_info["id"]
        self.log = logging.getLogger(f"task ({self.task_id})")

        super().__init__(isolated_network_mgr, docker_client=docker_client)
        self.image = image
        self.__vpn_manager = vpn_manager
        self.run_id = run_id
        self.task_id = task_info["id"]
        self.parent_id = get_parent_id(task_info)
        self.__tasks_dir = tasks_dir
        self.databases = databases
        self.data_volume_name = docker_volume_name
        self.node_name = node_name
        self.alpine_image = ALPINE_IMAGE if alpine_image is None else alpine_image
        self.proxy = proxy

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
        self.tmp_folder = "/mnt/tmp"
        self.data_folder = "/mnt/data"

        # keep track of the task status
        self.status: TaskStatus = TaskStatus.INITIALIZING

        # set device requests
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
            self.log.debug(f"- task id: {self.task_id}")
            self.log.debug(f"- result id: {self.task_id}")
            self.status = TaskStatus.UNKNOWN_ERROR
            raise AlgorithmContainerNotFound

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
            self.status = TaskStatus.CRASHED
        else:
            self.status = TaskStatus.COMPLETED
        return logs

    def get_results(self) -> bytes:
        """
        Read results output file of the algorithm container

        Returns
        -------
        bytes:
            Results of the algorithm container
        """
        with open(self.output_file, "rb") as fp:
            results = fp.read()
        return results

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
            self.log.info(f"Retrieving latest image: '{self.image}'")
            self.docker.images.pull(self.image)
        except docker.errors.APIError as e:
            self.log.warning("Failed to pull image: could not find image")
            if not local_exists:
                self.log.exception(e)
                self.status = TaskStatus.NO_DOCKER_IMAGE
                raise PermanentAlgorithmStartFail
            else:
                self.log.info("Using local image")
        except Exception as e:
            self.log.warning("Failed to pull image")
            if not local_exists:
                self.log.exception(e)
                self.status = TaskStatus.FAILED
                raise PermanentAlgorithmStartFail
            else:
                self.log.info("Using local image")

    def run(
        self,
        docker_input: bytes,
        tmp_vol_name: str,
        token: str,
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
        tmp_vol_name: str
            Name of temporary docker volume assigned to the algorithm
        token: str
            Bearer token that the container can use
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
        self.volumes = self._prepare_volumes(tmp_vol_name, token)
        self.log.debug(f"volumes: {self.volumes}")

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
            self.status = TaskStatus.START_FAILED
            raise UnknownAlgorithmStartFail(e)

        self.status = TaskStatus.ACTIVE
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

    def _prepare_volumes(self, tmp_vol_name: str, token: str) -> dict:
        """
        Generate docker volumes required to run the algorithm

        Parameters
        ----------
        tmp_vol_name: str
            Name of temporary docker volume assigned to the algorithm
        token: str
            Bearer token that the container can use

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
            ("token", token.encode("ascii")),
        ]

        for filename, data in io_files:
            filepath = os.path.join(self.task_folder_path, filename)

            with open(filepath, "wb") as fp:
                fp.write(data)

        volumes = {
            tmp_vol_name: {"bind": self.tmp_folder, "mode": "rw"},
        }

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
            self.log.warn("PROXY_SERVER_HOST not set, using " "host.docker.internal")
            self.log.debug(os.environ)
            proxy_host = "host.docker.internal"

        # define environment variables for the docker-container, the
        # host, port and api_path are from the local proxy server to
        # facilitate indirect communication with the central server
        # FIXME: we should only prepend data_folder if database_uri is a
        #   filename
        environment_variables = {
            "INPUT_FILE": f"{self.data_folder}/{self.task_folder_name}/input",
            "OUTPUT_FILE": f"{self.data_folder}/{self.task_folder_name}/output",
            "TOKEN_FILE": f"{self.data_folder}/{self.task_folder_name}/token",
            "TEMPORARY_FOLDER": self.tmp_folder,
            "HOST": f"http://{proxy_host}",
            "PORT": os.environ.get("PROXY_SERVER_PORT", 8080),
            "API_PATH": "",
        }

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

        for database in databases_to_use:
            if database["label"] not in self.databases:
                # In this case the algorithm might crash if it tries to access
                # the DATABASE_LABEL environment variable
                self.log.warning(
                    "A user specified a database that does not "
                    "exist. Available databases are: "
                    f"{self.databases.keys()}. This is likely to "
                    "result in an algorithm crash."
                )
                self.log.debug(f"User specified database: {database}")
            # define env vars for the preprocessing and extra parameters such
            # as query and sheet_name
            extra_params = (
                json.loads(database.get("parameters"))
                if database.get("parameters")
                else {}
            )
            for optional_key in ["query", "sheet_name", "preprocessing"]:
                if optional_key in extra_params:
                    env_var_value = (
                        extra_params[optional_key]
                        if optional_key != "preprocessing"
                        else json.dumps(extra_params[optional_key])
                    )
                    environment_variables[
                        f"{database['label'].upper()}_" f"{optional_key.upper()}"
                    ] = env_var_value

        environment_variables["USER_REQUESTED_DATABASE_LABELS"] = ",".join(
            [db["label"] for db in databases_to_use]
        )

        # Only prepend the data_folder is it is a file-based database
        # This allows algorithms to access multiple data sources at the
        # same time
        db_labels = []
        for label in self.databases:
            db = self.databases[label]

            uri_var_name = f"{label.upper()}_DATABASE_URI"
            environment_variables[uri_var_name] = (
                f"{self.data_folder}/{os.path.basename(db['uri'])}"
                if db["is_file"]
                else db["uri"]
            )

            type_var_name = f"{label.upper()}_DATABASE_TYPE"
            environment_variables[type_var_name] = db["type"]

            # Add optional database parameter settings, these can be used by
            # the algorithm (wrapper). Note that all env keys are prefixed
            # with DB_PARAM_ to avoid collisions with other environment
            # variables.
            if "env" in db:
                for key in db["env"]:
                    env_key = f"{label.upper()}_DB_PARAM_{key.upper()}"
                    environment_variables[env_key] = db["env"][key]

            db_labels.append(label)
        environment_variables["DB_LABELS"] = ",".join(db_labels)

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
                self.status = TaskStatus.FAILED
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
