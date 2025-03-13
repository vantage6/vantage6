import logging
import os
import time
import re
import base64

from typing import Tuple
from pathlib import Path
import uuid

from kubernetes import client as k8s_client, config, watch
from kubernetes.client import V1EnvVar
from kubernetes.client.rest import ApiException

from vantage6.cli.context.node import NodeContext
from vantage6.common import logger_name, get_database_config
from vantage6.common.globals import (
    DEFAULT_ALPINE_IMAGE,
    DEFAULT_DOCKER_REGISTRY,
    NodePolicy,
    ContainerEnvNames,
    STRING_ENCODING,
    ENV_VAR_EQUALS_REPLACEMENT,
)
from vantage6.common.enum import AlgorithmStepType, RunStatus, TaskDatabaseType
from vantage6.common.docker.addons import (
    get_digest,
    get_image_name_wo_tag,
)
from vantage6.common.client.node_client import NodeClient
from vantage6.node.globals import (
    ENV_VARS_NOT_SETTABLE_BY_NODE,
    KUBE_CONFIG_FILE_PATH,
    PROXY_SERVER_HOST,
    PROXY_SERVER_PORT,
    DATABASE_BASE_PATH,
    TASK_FILES_ROOT,
    JOB_POD_OUTPUT_PATH,
    JOB_POD_INPUT_PATH,
    JOB_POD_TOKEN_PATH,
    JOB_POD_SESSION_FOLDER_PATH,
    TASK_START_RETRIES,
    TASK_START_TIMEOUT_SECONDS,
)
from vantage6.node.util import get_parent_id
from vantage6.node.k8s.run_io import RunIO
from vantage6.node.k8s.exceptions import (
    PermanentAlgorithmStartFail,
    DataFrameNotFound,
)
from vantage6.node.k8s.data_classes import Result, ToBeKilled, KilledRun


class ContainerManager:

    def __init__(self, ctx: NodeContext, client: NodeClient):
        """
        Initialization of ``ContainerManager`` that handles communication with the
        Kubernetes cluster.

        Parameters
        ----------
        ctx: NodeContext
            Context object from which some settings are obtained
        """
        self.log = logging.getLogger(logger_name(__name__))
        self.log.debug("Initializing ContainerManager")
        self.ctx = ctx
        self.client = client

        # Instanced within a pod
        if not os.path.exists(KUBE_CONFIG_FILE_PATH):
            raise ValueError(
                "Kubernetes configuration file not found at ",
                KUBE_CONFIG_FILE_PATH,
            )

        # Default mount location defined on POD configuration
        config.load_kube_config(KUBE_CONFIG_FILE_PATH)

        # The `local_data_dir` refers to the location where this node can write files
        # to. When this node instance needs to create a volume mount for a container,
        # it needs to refer to the location where the file is stored on the host system,
        # for this we use the `host_data_dir`.
        self.local_data_dir = TASK_FILES_ROOT
        self.host_data_dir = self.ctx.config["task_dir"]

        self.databases = self._set_database(self.ctx.config["databases"])

        # before a task is executed it gets exposed to these policies
        self._policies = self._setup_policies(self.ctx.config)

        # K8S Batch API
        self.batch_api = k8s_client.BatchV1Api()
        # K8S Core API instance
        self.core_api = k8s_client.CoreV1Api()
        # namespace to run the tasks in
        self.task_namespace = self.ctx.config["task_namespace"]

        # labels to identify the task jobs of this node
        self.task_job_labels = {"node_id": self.ctx.identifier}
        self.task_job_label_selector = ",".join(
            [f"{k}={v}" for k, v in self.task_job_labels.items()]
        )

    def ensure_task_namespace(self) -> bool:
        """
        Ensure that the namespace for the task exists and jobs can be created in it.
        If it does not exist, try to create it

        Returns
        -------
        bool
            True if the namespace exists or was created and is writeable, False
            otherwise
        """
        # TODO consider using hierarchical namespaces, it may be easier to create
        # those in a large cluster environment
        # https://kubernetes.io/blog/2020/08/14/introducing-hierarchical-namespaces/
        task_namespace_exists = False
        try:
            self.core_api.read_namespace(self.task_namespace)
            task_namespace_exists = True
        except ApiException as exc:
            # return False if the namespace exists but we cannot read it
            if exc.status != 404:
                return False

        if not task_namespace_exists:
            self.log.warning(
                "Task namespace '%s' does not exist, creating it now.",
                self.task_namespace,
            )
            namespace = k8s_client.V1Namespace(
                metadata=k8s_client.V1ObjectMeta(name=self.task_namespace)
            )
            try:
                self.core_api.create_namespace(namespace)
            except ApiException as exc:
                self.log.error(
                    "Failed to create task namespace '%s': %s", self.task_namespace, exc
                )
                return False

        # try to see if jobs can be created in the cluster - if not, tasks cannot be
        # created so we return False
        test_pod_name = str(uuid.uuid4())
        try:
            self.core_api.create_namespaced_pod(
                namespace=self.task_namespace,
                body=k8s_client.V1Pod(
                    metadata=k8s_client.V1ObjectMeta(name=test_pod_name),
                    spec=k8s_client.V1PodSpec(
                        containers=[
                            k8s_client.V1Container(
                                # TODO ensure image is an image that can always be
                                # pulled by the node
                                name="test-container",
                                image=(
                                    f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_ALPINE_IMAGE}"
                                ),
                            )
                        ]
                    ),
                ),
            )
        except ApiException as exc:
            self.log.error(
                "Failed to create test pod in task namespace '%s': %s",
                self.task_namespace,
                exc,
            )
            return False
        # clean up the test pod
        self.core_api.delete_namespaced_pod(test_pod_name, self.task_namespace)

        return True

    def _setup_policies(self, config: dict) -> dict:
        """
        Set up policies for the node.

        Parameters
        ----------
        config: dict
            Configuration dictionary

        Returns
        -------
        dict
            Dictionary with the policies
        """
        policies = config.get("policies", {})
        if not policies or (
            not policies.get(NodePolicy.ALLOWED_ALGORITHMS)
            and not policies.get(NodePolicy.ALLOWED_ALGORITHM_STORES)
        ):
            self.log.warning(
                "No policies on allowed algorithms have been set for this node!"
            )
            self.log.warning(
                "This means that all algorithms are allowed to run on this node."
            )
        return policies

    def _set_database(self, config_databases: dict | list) -> dict:
        """
        Set database location and whether or not it is a file

        Parameters
        ----------
        databases: dict | list
            databases as specified in the config file

        Returns
        -------
        dict
            Dictionary with the information about the databases
        """
        db_labels = [db["label"] for db in config_databases]

        databases = {}
        for label in db_labels:

            db_config = get_database_config(config_databases, label)

            # The URI on the host system. This can either be a path to a file or folder
            # or an address to a service.
            uri = db_config["uri"]

            # In case we are dealing with a file or directory and when running the node
            # instance in a POD, our internal path to that file or folder is different.
            # At this point we are not sure what the type of database is so we just
            # see wether it exists or not. In case it does, we create a `local_uri` that
            # points to the file or folder in the POD. We keep the original URI as we
            # need it when we are creating new volume mounts for the algorithm
            # containers
            local_uri = uri
            # TODO v5+ we should ensure that DATABASE_BASE_PATH is also used in the CLI
            # so that we can be sure this file exists. From the type we could then
            # derive if it's a file or directory, and it may be entirely unneccesary in
            # that case to mount the database files/dirs into the node container.
            tmp_uri = Path(DATABASE_BASE_PATH) / f"{label}.{db_config['type']}"

            db_is_file = tmp_uri.exists() and tmp_uri.is_file()
            db_is_dir = tmp_uri.exists() and tmp_uri.is_dir()

            if db_is_file or db_is_dir:
                local_uri = str(tmp_uri)

            databases[label] = {
                "uri": uri,
                "local_uri": local_uri,
                "is_file": db_is_file,
                "is_dir": db_is_dir,
                "type": db_config["type"],
                "env": db_config.get("env", {}),
            }

        self.log.debug("Databases: %s", databases)
        return databases

    def run(
        self,
        run_id: int,
        task_info: dict,
        image: str,
        docker_input: bytes,
        session_id: int,
        token: str,
        databases_to_use: list[str],
        action: AlgorithmStepType,
    ) -> RunStatus:
        """
        Run a vantage6 algorithm on the Kubernetes cluster.

        Parameters
        ----------
        run_id: int
            Server run identifier
        task_info: dict
            Dictionary with task information *** Includes parent-algorithm id
        image: str
            Docker image name
        docker_input: bytes
            Input that can be read by docker container
        session_id: int
            ID of the session
        token: str
            Bearer token that the container can use
        databases_to_use: list[str]
            Labels of the databases to use
        action: AlgorithmStepType
            The action to perform

        Returns
        -------
        RunStatus
            Returns the status of the run
        """
        self.log.debug("Setting up algorithm run %s", run_id)
        # In case we are dealing with a data-extraction or prediction task, we need to
        # know the dataframe that is being created or modified by the algorithm.
        df_details = task_info.get("dataframe", {})

        run_io = RunIO(
            run_id,
            session_id,
            action,
            self.client,
            df_details,
            self.local_data_dir,
        )

        # Verify that an allowed image is used
        if not self.is_docker_image_allowed(image, task_info):
            self.log.critical(f"Docker image {image} is not allowed on this Node!")
            return RunStatus.NOT_ALLOWED

        # Check that this task is not already running
        if self.is_running(run_io.container_name):
            self.log.warning(
                f"Task (run_id={run_id}) is already being executed, discarding task"
            )
            return RunStatus.ACTIVE

        task_id = task_info["id"]
        parent_task_id = get_parent_id(task_info)

        try:
            _volumes, _volume_mounts, env_vars = self._create_volume_mounts(
                run_io=run_io,
                docker_input=docker_input,
                token=token,
                databases_to_use=databases_to_use,
            )
        except PermanentAlgorithmStartFail as e:
            self.log.warning(e)
            return RunStatus.FAILED
        except DataFrameNotFound as e:
            self.log.info(e)
            return RunStatus.DATAFRAME_NOT_FOUND
        except Exception as e:
            self.log.exception(e)
            return RunStatus.UNKNOWN_ERROR

        # Set environment variables for the algorithm client. This client is used
        # to communicate from the algorithm to the vantage6 server through the proxy.
        env_vars[ContainerEnvNames.HOST.value] = os.environ.get(
            "PROXY_SERVER_HOST", PROXY_SERVER_HOST
        )
        env_vars[ContainerEnvNames.PORT.value] = os.environ.get(
            "PROXY_SERVER_PORT", str(PROXY_SERVER_PORT)
        )
        env_vars[ContainerEnvNames.API_PATH.value] = ("",)

        env_vars[ContainerEnvNames.FUNCTION_ACTION.value] = action.value

        # Encode the environment variables to avoid issues with special characters and
        # for security reasons. The environment variables are encoded in base64.
        io_env_vars = []
        env_vars = self._encode_environment_variables(env_vars)
        for key, value in env_vars.items():
            io_env_vars.append(k8s_client.V1EnvVar(name=key, value=value))

        try:
            self._validate_environment_variables(env_vars)
        except PermanentAlgorithmStartFail as e:
            self.log.warning(e)
            return RunStatus.FAILED

        container = k8s_client.V1Container(
            name=run_io.container_name,
            image=image,
            tty=True,
            volume_mounts=_volume_mounts,
            env=io_env_vars,
        )

        job_metadata = k8s_client.V1ObjectMeta(
            name=run_io.container_name,
            annotations={
                "run_id": str(run_io.run_id),
                "task_id": str(task_id),
                "task_parent_id": str(parent_task_id),
                "action": str(action.value),
                "session_id": str(session_id),
                "df_name": df_details.get("name") if df_details else "",
                "df_id": str(df_details.get("id")) if df_details else "",
                "df_label": df_details.get("label") if df_details else "",
            },
            labels=self.task_job_labels,
        )

        # Define the job
        job = k8s_client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=job_metadata,
            spec=k8s_client.V1JobSpec(
                template=k8s_client.V1PodTemplateSpec(
                    metadata=k8s_client.V1ObjectMeta(
                        labels={"app": run_io.container_name}
                    ),
                    spec=k8s_client.V1PodSpec(
                        containers=[container],
                        volumes=_volumes,
                        restart_policy="Never",
                    ),
                ),
                backoff_limit=TASK_START_RETRIES,
            ),
        )

        self.log.info(
            "Creating namespaced K8S job for task_id=%s and run_id=%s.", task_id, run_id
        )
        self.batch_api.create_namespaced_job(namespace=self.task_namespace, body=job)

        # Wait till the job is up and running. The job is considered to be running
        # when the POD created by the job reports at least a 'Running' state. The states
        # that a POD can report:
        #                      - Succeeded
        #                     /
        # Pending - Running ---- Failed
        #                     \
        #                      - Unknown
        #

        # Kubernetes will automatically retry the job ``backoff_limit`` times. According
        # to the Pod's backoff failure policy, it will have a failed status only after
        # the last failed retry.
        start_time = time.time()

        # Wait until the POD is running. This method is blocking until the POD is
        # running or a timeout is reached.
        # TODO even though the timeout is reached, the POD could still be running
        # TODO we could make this non-blocking by keeping track of the started jobs
        #     and checking their status in a separate thread
        # TODO in the previous `DockerTaskManager` a few checks where performed to
        #      tackle any issues with the prerequisites. For example it checked wether
        #      the dataframe requested by the user was available. We should re-implement
        #      these checks here.

        # stackoverflow.com/questions/57563359/how-to-properly-update-the-status-of-a-job
        # kubernetes.io/docs/concepts/workloads/controllers/job/#pod-backoff-failure-
        # policy
        while True:

            pods = self.core_api.list_namespaced_pod(
                namespace=self.task_namespace,
                label_selector=f"app={run_io.container_name}",
            )

            if pods.items:

                # The container was created and has at least the `pending` state. Wait
                # until it reports either an `active` or `failed` state.
                self.log.info(
                    "Job POD (label %s) with %s items created successfully in %s "
                    "namespace. Waiting until it is running...",
                    run_io.container_name,
                    len(pods.items),
                    self.task_namespace,
                )
                status = self.__wait_until_pod_running(
                    label=f"app={run_io.container_name}"
                )
                self.log.info(
                    "Job POD (label %s) is now running!", run_io.container_name
                )

                return status

            elif time.time() - start_time > TASK_START_TIMEOUT_SECONDS:
                self.log.error(
                    "Time out waiting for Job POD (label %s) to start.",
                    run_io.container_name,
                )
                return RunStatus.UNKNOWN_ERROR

            time.sleep(1)

    def __wait_until_pod_running(self, label: str) -> RunStatus:
        """
        Wait until the POD created by a job is running.

        Parameters
        ----------
        label: str
            Label of the POD for this run (kubernetes job)


        Returns
        -------
        RunStatus
            Status of the run
        """
        # Start watching for events on the pod
        w = watch.Watch()

        for event in w.stream(
            func=self.core_api.list_namespaced_pod,
            namespace=self.task_namespace,
            label_selector=label,
            # TODO v5+ this timeout should be as a global. Is 120 seconds a good value?
            timeout_seconds=120,
        ):
            pod_phase = event["object"].status.phase

            # TODO we need to also check for the 'Failed' status, we could have
            # missed that event.
            if pod_phase == "Running":
                w.stop()
                return RunStatus.ACTIVE

        # This point is reached after timeout
        return RunStatus.UNKNOWN_ERROR

    def _create_run_mount(
        self,
        volume_name: str,
        host_path: str | Path,
        mount_path: str,
        type_: str | None = None,
        read_only: bool = False,
    ) -> Tuple[k8s_client.V1Volume, k8s_client.V1VolumeMount]:
        """
        Create a volume and its corresponding volume mount

        Parameters
        ----------
        volume_name: str
            Name of the volume
        host_path: str | Path
            Path to the host, could be a file or a folder
        mount_path: str
            Path where the ``host_path`` is going to be mounted
        type_: str, optional
            Type of the volume
        read_only: bool
            Whether the volume is read-only or not in the mount

        Returns
        -------
        V1Volume, V1VolumeMount
            Tuple with the volume and volume mount
        """
        host_path = str(host_path)

        volume = k8s_client.V1Volume(
            name=volume_name,
            host_path=k8s_client.V1HostPathVolumeSource(path=host_path, type=type_),
        )

        vol_mount = k8s_client.V1VolumeMount(
            name=volume_name,
            mount_path=mount_path,
            read_only=read_only,
        )

        return (volume, vol_mount)

    def _create_volume_mounts(
        self,
        run_io: RunIO,
        docker_input: bytes,
        token: str,
        databases_to_use: list[str],
    ) -> Tuple[
        list[k8s_client.V1Volume], list[k8s_client.V1VolumeMount], list[V1EnvVar]
    ]:
        """
        Create all volumes and volume mounts required by the algorithm/job.

        Parameters
        ----------
        run_io: RunIO
            RunIO object that contains information about the run
        docker_input: bytes
            Input that can be read by the algorithm container
        token: str
            Bearer token that the container can use to communicate with the server
        databases_to_use: list[str]
            Labels of the databases to use

        Returns
        -------
        list[client.V1Volume], list[client.V1VolumeMount], list[V1EnvVar]
            a tuple with (1) the created volume names and (2) their corresponding volume
            mounts and (3) the list of the environment variables required by the
            algorithms to use such mounts.

        Notes
        -----
        In this method volume-claims could be used instead of 'host_path' volumes to
        decouple vantage6 file management from the storage provider (NFS, GCP, etc).
        However, persistent-volumes (from which volume-claims are be created), present
        a risk when used on local file systems. In particular, if two VC are created
        from the same PV, both would end sharing the same files. e.g. define the volume
        for temporal data:

        ```python
        tmp_volume = client.V1Volume(
            name=f'task-{str_run_id}-tmp',
            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                claim_name=tmp_vol_name
            )
        )
        ```
        """
        volumes: list[k8s_client.V1Volume] = []
        vol_mounts: list[k8s_client.V1VolumeMount] = []

        # Create algorithm's input and token files before creating volume mounts with
        # them (relative to the node's file system: POD or host)
        input_file_path, output_file_path, token_file_path = run_io.create_files(
            docker_input, b"", token.encode("ascii")
        )

        # Create the volumes and corresponding volume mounts for the input, output and
        # token files.
        output_volume, output_mount = self._create_run_mount(
            volume_name=run_io.output_volume_name,
            host_path=Path(self.host_data_dir) / output_file_path,
            mount_path=JOB_POD_OUTPUT_PATH,
            type_="File",
            read_only=False,
        )

        input_volume, input_mount = self._create_run_mount(
            volume_name=run_io.input_volume_name,
            host_path=Path(self.host_data_dir) / input_file_path,
            type_="File",
            mount_path=JOB_POD_INPUT_PATH,
        )

        token_volume, token_mount = self._create_run_mount(
            volume_name=run_io.token_volume_name,
            host_path=Path(self.host_data_dir) / token_file_path,
            type_="File",
            mount_path=JOB_POD_TOKEN_PATH,
        )

        session_volume, session_mount = self._create_run_mount(
            volume_name=run_io.session_name,
            host_path=Path(self.host_data_dir) / run_io.session_folder,
            type_="Directory",
            mount_path=JOB_POD_SESSION_FOLDER_PATH,
        )

        volumes.extend([output_volume, input_volume, token_volume, session_volume])
        vol_mounts.extend([output_mount, input_mount, token_mount, session_mount])

        # The environment variables are expected by the algorithm containers in order
        # to access the input, output and token files.
        environment_variables = {
            ContainerEnvNames.OUTPUT_FILE.value: JOB_POD_OUTPUT_PATH,
            ContainerEnvNames.INPUT_FILE.value: JOB_POD_INPUT_PATH,
            ContainerEnvNames.TOKEN_FILE.value: JOB_POD_TOKEN_PATH,
            # TODO we only do not need to pass this when the action is `data extraction`
            ContainerEnvNames.SESSION_FOLDER.value: JOB_POD_SESSION_FOLDER_PATH,
            ContainerEnvNames.SESSION_FILE.value: os.path.join(
                JOB_POD_SESSION_FOLDER_PATH, run_io.session_state_file_name
            ),
        }

        # Bind-mounting all the CSV files (read only) defined on the configuration file
        # TODO bind other input data types
        # TODO include only the ones given in the 'databases_to_use parameter
        # TODO distinguish between the different actions
        if run_io.action == AlgorithmStepType.DATA_EXTRACTION:
            environment_variables[ContainerEnvNames.USER_REQUESTED_DATABASES.value] = (
                ",".join([db["label"] for db in databases_to_use]),
            )
            # In case we are dealing with a file based database, we need to create an
            # additional volume mount for the database file. In case it is an URI the
            # URI should be reachable from the container.
            self._validate_source_database(databases_to_use)
            # A always has 1 source database to use in the extraction step. This
            # is validated in the previous method.
            # TODO v5+ if the validate function above raises error, this is somehow
            # still reached?!
            source_database = databases_to_use[0]
            db = self.databases[source_database["label"]]
            if db["is_file"] or db["is_dir"]:
                db_volume, db_mount = self._create_run_mount(
                    volume_name=f"task-{run_io.run_id}-db-{source_database['label']}",
                    host_path=db["uri"],
                    mount_path=db["local_uri"],
                    type_="File" if db["is_file"] else "Directory",
                    read_only=True,
                )
                volumes.append(db_volume)
                vol_mounts.append(db_mount)

            environment_variables[ContainerEnvNames.DATABASE_URI.value] = db[
                "local_uri"
            ]
            environment_variables[ContainerEnvNames.DATABASE_TYPE.value] = db["type"]

            # additional environment variables for the database. These will be stored
            # as {PREFIX}{KEY}=value in the container
            if "env" in db:
                for key in db["env"]:
                    env_key = f"{ContainerEnvNames.DB_PARAM_PREFIX}{key.upper()}"
                    environment_variables[env_key] = db["env"][key]

        else:
            # In the other cases (preprocessing, compute, ...) we are dealing with a
            # dataframe in a session. So we only need to validate that the dataframe is
            # available in the session.
            self._validate_dataframes(databases_to_use, run_io)

            environment_variables[ContainerEnvNames.USER_REQUESTED_DATAFRAMES.value] = (
                ",".join([db["name"] for db in databases_to_use])
            )

        return volumes, vol_mounts, environment_variables

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
                raise PermanentAlgorithmStartFail(msg)

    def _validate_dataframes(self, databases_to_use: list[dict], run_io: RunIO) -> None:
        """
        Validates that all provided databases are of type 'dataframe' and that the
        requested names exist in the session folder.

        Parameters
        ----------
        databases_to_use: list[dict]
            A list of dictionaries where each dictionary represents a database
            with a 'type' and 'label'.
        run_io: RunIO
            RunIO object that contains information about the run

        Raises
        ------
        PermanentAlgorithmStartFail:
            If any database is not of type 'dataframe'.
        DataFrameNotFound:
            If any requested df name is not found in the session folder.
        """

        if not all(df["type"] == TaskDatabaseType.DATAFRAME for df in databases_to_use):
            self.log.error(
                "All databases used in the algorithm must be of type '%s'.",
                TaskDatabaseType.DATAFRAME.value,
            )
            raise PermanentAlgorithmStartFail()

        # Validate that the requested dataframes exist. At this point they need to as
        # we are about to start the task.
        requested_dataframes = {db["label"] for db in databases_to_use}
        available_dataframes = {
            file_.stem for file_ in Path(run_io.local_session_folder).glob("*.parquet")
        }
        # check that requested dataframes are a subset of available dataframes
        if not requested_dataframes.issubset(available_dataframes):
            self.log.error("Requested dataframe(s) not found in session folder.")
            self.log.debug("Requested dataframes: %s", requested_dataframes)
            self.log.debug("Available dataframes: %s", available_dataframes)
            problematic_dfs = requested_dataframes - available_dataframes
            raise DataFrameNotFound(
                f"User requested dataframes '{problematic_dfs}' which are not available"
                " in the session folder. Available dataframes are: "
                f"{available_dataframes}."
            )

    def _validate_source_database(self, databases_to_use: list[dict]) -> None:
        """
        Validates the source database configuration for the data extraction step.
        This method checks if the provided list of databases contains exactly one
        database, and if that database is of type 'source' and exists in the
        available databases.

        Parameters
        ----------
        databases_to_use : list[dict]
            A list of dictionaries where each dictionary represents a database
            configuration.

        Raises
        ------
        PermanentAlgorithmStartFail
            If the validation fails due to any of the conditions not being met.
        """

        ok = True
        if len(databases_to_use) > 1:
            self.log.error("Only one database can be used in the data extraction step.")
            ok = False

        if len(databases_to_use) == 0:
            self.log.error("No database is provided for the data extraction step.")
            ok = False

        source_database = databases_to_use[0]

        if source_database["type"] != "source":
            self.log.error(
                "The database used in the data extraction step must be of type "
                "'source'."
            )
            ok = False

        if source_database["label"] not in self.databases.keys():
            self.log.error(
                "The database used in the data extraction step does not exist."
            )
            ok = False

        if not ok:
            raise PermanentAlgorithmStartFail()

    def is_docker_image_allowed(self, evaluated_img: str, task_info: dict) -> bool:
        """
        Checks the docker image name.

        Against a list of regular expressions as defined in the configuration
        file. If no expressions are defined, all docker images are accepted.

        Parameters
        ----------
        evaluated_img: str
            URI of the docker image of which we are checking if it is allowed
        task_info: dict
            Dictionary with information about the task

        Returns
        -------
        bool
            Whether docker image is allowed or not
        """
        # check if algorithm matches any of the regex cases
        allowed_algorithms = self._policies.get(NodePolicy.ALLOWED_ALGORITHMS)
        allowed_stores = self._policies.get(NodePolicy.ALLOWED_ALGORITHM_STORES)
        allow_either_whitelist_or_store = self._policies.get(
            "allow_either_whitelist_or_store", False
        )

        # check if user or their organization is allowed
        allowed_users = self._policies.get(NodePolicy.ALLOWED_USERS, [])
        allowed_orgs = self._policies.get(NodePolicy.ALLOWED_ORGANIZATIONS, [])
        if allowed_users or allowed_orgs:
            is_allowed = self.client.check_user_allowed_to_send_task(
                allowed_users,
                allowed_orgs,
                task_info["init_org"]["id"],
                task_info["init_user"]["id"],
            )
            if not is_allowed:
                self.log.warning(
                    "A task was sent by a user or organization that this node does not "
                    "allow to start tasks."
                )
                return False

        algorithm_whitelisted = False
        if allowed_algorithms:
            if isinstance(allowed_algorithms, str):
                allowed_algorithms = [allowed_algorithms]
            try:
                evaluated_img_wo_tag = get_image_name_wo_tag(evaluated_img)
            except Exception as exc:
                self.log.warning(
                    "Could not parse image with name %s: %s",
                    evaluated_img,
                    exc,
                )
                evaluated_img_wo_tag = None
            for allowed_algo in allowed_algorithms:
                if not self._is_regex_pattern(allowed_algo):
                    try:
                        allowed_wo_tag = get_image_name_wo_tag(allowed_algo)
                    except Exception as exc:
                        self.log.warning(
                            "Could not parse allowed_algorithm policy with name %s: %s",
                            allowed_algo,
                            exc,
                        )
                        self.log.warning("Skipping policy as it cannot be parsed")
                        continue  # skip policy as it cannot be parsed
                    if allowed_algo == evaluated_img:
                        # OK if allowed algorithm and provided algorithm match exactly
                        algorithm_whitelisted = True
                        break
                    elif allowed_algo == evaluated_img_wo_tag:
                        # OK if allowed algorithm is an image name without a tag, and
                        # the provided image is the same but includes extra tag
                        algorithm_whitelisted = True
                        break
                    elif allowed_wo_tag == evaluated_img_wo_tag:
                        # The allowed image and the evaluated image are indeed the same
                        # image but the allowed image only allows certain tags or sha's.
                        # Gather the digests of the images and compare them - if they
                        # are the same, the image is allowed.
                        # Note that by comparing the digests, we also take into account
                        # the situation where e.g. the allowed image has a tag, but the
                        # evaluated image has a sha256.
                        # TODO fix v5+, the self.docker is no longer available
                        digest_evaluated_image = get_digest(
                            evaluated_img, client=self.docker
                        )
                        if not digest_evaluated_image:
                            self.log.warning(
                                "Could not obtain digest for image %s",
                                evaluated_img,
                            )
                        digest_policy_image = get_digest(
                            allowed_algo, client=self.docker
                        )
                        if not digest_policy_image:
                            self.log.warning(
                                "Could not obtain digest for image %s", allowed_algo
                            )
                        if (
                            digest_evaluated_image
                            and digest_policy_image
                            and (digest_evaluated_image == digest_policy_image)
                        ):
                            algorithm_whitelisted = True
                            break
                else:
                    expr_ = re.compile(allowed_algo)
                    if expr_.match(evaluated_img):
                        algorithm_whitelisted = True

        store_whitelisted = False
        if allowed_stores:
            # get the store from the task_info
            try:
                store_id = task_info["algorithm_store"]["id"]
            except Exception:
                store_id = None
            if store_id:
                store = self.client.algorithm_store.get(store_id)
                store_from_task = store["url"]
                # check if the store matches any of the regex cases
                if isinstance(allowed_stores, str):
                    allowed_stores = [allowed_stores]
                for store in allowed_stores:
                    if not self._is_regex_pattern(store):
                        # check if string matches exactly
                        if store == store_from_task:
                            store_whitelisted = True
                    else:
                        expr_ = re.compile(store)
                        if expr_.match(store_from_task):
                            store_whitelisted = True

        allowed_from_whitelist = not allowed_algorithms or algorithm_whitelisted
        allowed_from_store = not allowed_stores or store_whitelisted
        if allow_either_whitelist_or_store:
            # if we allow an algorithm if it is defined in the whitelist or the store,
            # we return True if either the algorithm or the store is whitelisted
            allowed = allowed_from_whitelist or allowed_from_store
        else:
            # only allow algorithm if it is allowed for both the allowed_algorithms and
            # the allowed_algorithm_stores
            allowed = allowed_from_whitelist and allowed_from_store

        if not allowed:
            self.log.warning(
                "This node does not allow the algorithm %s to run!", evaluated_img
            )

        return allowed

    @staticmethod
    def _is_regex_pattern(pattern: str) -> bool:
        """
        Check if a string just a string or if it is a regex pattern. Note that there is
        no failsafe way to do this so we make a best effort.

        Note, for instance, that if a user provides the allowed algorithm "some.name",
        we will interpret this as a regular string. This prevents that "someXname" is
        allowed as well. The user is thus not able to define a regex pattern with only
        a dot as special character. However we expect that this use case is extremely
        rare - not doing so is likely to lead to regex's that lead to unintended
        algorithms passing the filter criteria.

        Parameters
        ----------
        pattern: str
            String to be checked

        Returns
        -------
        bool
            Returns False if the pattern is a normal string, True if it is a regex.
        """
        # Inspired by
        # https://github.com/corydolphin/flask-cors/blob/main/flask_cors/core.py#L254.
        common_regex_chars = [
            "*",
            "\\",
            "?",
            "$",
            "^",
            "[",
            "]",
            "(",
            ")",
            "{",
            "}",
            "|",
            "+",
            "\.",
        ]
        # Use common characters used in regular expressions as a proxy
        # for if this string is in fact a regex.
        return any((c in pattern for c in common_regex_chars))

    def is_running(self, label: str) -> bool:
        """
        Check if a container is already running for a certain run.

        Parameters
        ----------
        label: str
            Label of the container constructed from the `run_id`

        Returns
        -------
        bool
            Whether or not algorithm container is currently running
        """
        pods = self.core_api.list_namespaced_pod(
            namespace=self.task_namespace,
            label_selector=f"app={label}",
        )
        return True if pods.items else False

    def process_next_completed_job(self) -> Result:
        """
        Wait until a job is completed and process it.

        This method is blocking until a job is completed. It checks the status of the
        kubernetes jobs and returns the results of the first completed job. The results
        are then sent back to the server.

        Returns
        -------
        Result
            Result of the completed job
        """
        self.log.info("Waiting for a completed job to process")
        # wait until there is at least one completed job available (successful or
        # failed) other statuses (pending/running/unknown) are ignored
        completed_job = False
        while not completed_job:

            # Get all jobs from the task namespace for this node
            jobs = self.batch_api.list_namespaced_job(
                self.task_namespace, label_selector=self.task_job_label_selector
            )
            if not jobs.items:
                time.sleep(1)
                continue

            # Create a list of failed or succeeded jobs
            finished_jobs = [
                job for job in jobs.items if job.status.succeeded or job.status.failed
            ]

            if not finished_jobs:
                time.sleep(1)
                continue

            # Check if any of the jobs is completed
            for job in finished_jobs:

                # Create helper object to process the output of the job
                run_io = RunIO.from_dict(
                    job.metadata.annotations, self.client, self.local_data_dir
                )
                results, status = (
                    run_io.process_output()
                    if job.status.succeeded
                    else (b"", RunStatus.CRASHED)
                )

                try:
                    logs = self.__get_job_pod_logs(
                        run_io=run_io, namespace=self.task_namespace
                    )
                except Exception as e:
                    self.log.warning(
                        f"Error while getting logs of job {run_io.container_name}: {e}"
                    )
                    logs = ["error while getting logs"]

                # logs are saved as string instead of list[str]
                logs = "\n".join(logs)

                self.log.info(
                    "Sending results of run_id=%s and task_id=%s back to the server",
                    run_io.run_id,
                    job.metadata.annotations["task_id"],
                )

                result = Result(
                    run_id=run_io.run_id,
                    task_id=job.metadata.annotations["task_id"],
                    logs=logs,
                    data=results,
                    status=status,
                    parent_id=job.metadata.annotations["task_parent_id"],
                )

                self.__delete_job_related_pods(
                    run_io=run_io, namespace=self.task_namespace
                )
                completed_job = True

        return result

    def __get_job_pod_logs(self, run_io: str, namespace: str) -> list[str]:
        """
        Get the logs generated by the PODs created by a job.

        If there are multiple PODs created by the job (e.g., due to multiple failed
        execution attempts -see backofflimit setting-) all the POD logs are merged as
        one.
        """

        pods_tty_logs = []

        job_selector = f"job-name={run_io.container_name}"
        job_pods_list = self.core_api.list_namespaced_pod(
            namespace, label_selector=job_selector
        )

        for job_pod in job_pods_list.items:
            self.log.info(
                f"Getting logs from POD {job_pod.metadata.name}, created by job "
                f"{run_io.run_id}"
            )

            pod_log = self.core_api.read_namespaced_pod_log(
                name=job_pod.metadata.name,
                namespace=self.task_namespace,
                _preload_content=True,
            )

            pods_tty_logs.append(
                f"LOGS of POD {job_pod.metadata.name} (created by job "
                f"{run_io.container_name}) \n\n {pod_log} \n\n\n"
            )

        return pods_tty_logs

    def __delete_job_related_pods(self, run_io: RunIO, namespace: str):
        """
        Deletes all the PODs created by a Kubernetes job in a given namespace
        """
        self.log.info(
            "Cleaning up kubernetes Job %s (run_id = %s) and related PODs",
            run_io.container_name,
            run_io.run_id,
        )

        self.__delete_job(run_io.container_name, namespace)

        job_selector = f"job-name={run_io.container_name}"
        job_pods_list = self.core_api.list_namespaced_pod(
            namespace, label_selector=job_selector
        )
        for job_pod in job_pods_list.items:
            self.__delete_pod(job_pod.metadata.name, namespace)

    def __delete_job(self, job_name: str, namespace: str) -> None:
        """
        Deletes a job in a given namespace

        Parameters
        ----------
        job_name: str
            Name of the job
        namespace: str
            Namespace where the job is located
        """
        self.log.info(
            "Cleaning up kubernetes Job %s and related PODs",
            job_name,
        )
        try:
            # Check if the job exists before attempting to delete it
            job = self.batch_api.read_namespaced_job(name=job_name, namespace=namespace)
            if job:
                self.batch_api.delete_namespaced_job(name=job_name, namespace=namespace)
            else:
                self.log.warning(
                    "Job %s not found in namespace %s, skipping deletion",
                    job_name,
                    namespace,
                )
        except ApiException as exc:
            if exc.status == 404:
                self.log.warning(
                    "Job %s not found in namespace %s, skipping deletion",
                    job_name,
                    namespace,
                )
            else:
                self.log.error("Exception when deleting namespaced job: %s", exc)

    def __delete_pod(self, pod_name: str, namespace: str) -> None:
        """
        Deletes a job in a given namespace

        Parameters
        ----------
        pod_name: str
            Name of the job
        namespace: str
            Namespace where the job is located
        """
        self.log.info(
            "Cleaning up kubernetes pod %s in namespace %s", pod_name, namespace
        )
        try:
            # Check if the job exists before attempting to delete it
            job = self.core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
            if job:
                self.core_api.delete_namespaced_pod(name=pod_name, namespace=namespace)
            else:
                self.log.warning(
                    "Pod %s not found in namespace %s, skipping deletion",
                    pod_name,
                    namespace,
                )
        except ApiException as exc:
            if exc.status == 404:
                self.log.warning(
                    "Pod %s not found in namespace %s, skipping deletion",
                    pod_name,
                    namespace,
                )
            else:
                self.log.error("Exception when deleting namespaced job: %s", exc)

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
            Finally, '=' is replaced by less sensitive characters to prevent
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

    # def cleanup_tasks(self) -> list[KilledRun]:
    #     """
    #     Stop all active tasks

    #     Returns
    #     -------
    #     list[KilledRun]:
    #         List of information on tasks that have been killed
    #     """
    #     pass

    # def cleanup(self) -> None:
    #     """
    #     Stop all active tasks and delete the isolated network

    #     Note: the temporary docker volumes are kept as they may still be used
    #     by a parent container
    #     """
    #     # note: the function `cleanup_tasks` returns a list of tasks that were
    #     # killed, but we don't register them as killed so they will be run
    #     # again when the node is restarted
    #     pass

    # def login_to_registries(self, registries: list = []) -> None:
    #     """
    #     Login to the docker registries

    #     Parameters
    #     ----------
    #     registries: list
    #         list of registries to login to
    #     """
    #     pass

    # def link_container_to_network(self, container_name: str, config_alias: str) -> None:
    #     """
    #     Link a docker container to the isolated docker network

    #     Parameters
    #     ----------
    #     container_name: str
    #         Name of the docker container to be linked to the network
    #     config_alias: str
    #         Alias of the docker container defined in the config file
    #     """
    #     pass

    # def kill_selected_tasks(
    #    self, org_id: int, kill_list: list[ToBeKilled] = None
    # ) -> list[KilledRun]:
    #   pass

    def kill_tasks(
        self, org_id: int, kill_list: list[ToBeKilled] = None
    ) -> list[KilledRun]:
        """
        Kill tasks currently running on this node.

        Parameters
        ----------
        org_id: int
            The organization id of this node
        kill_list: list[ToBeKilled] (optional)
            A list of info on tasks that should be killed. If the list
            is not specified, all running algorithm containers will be killed.

        Returns
        -------
        list[KilledRun]
            List of dictionaries with information on killed tasks
        """

        if kill_list:
            killed_runs = self.kill_selected_tasks(org_id=org_id, kill_list=kill_list)
        else:
            # received instruction to kill all tasks on this node
            self.log.warn(
                "Received instruction from server to kill all algorithms "
                "running on this node. Executing that now..."
            )
            killed_runs = self.cleanup_tasks()
            if len(killed_runs):
                self.log.warn(
                    "Killed the following run ids as instructed via socket:"
                    f" {', '.join([str(r.run_id) for r in killed_runs])}"
                )
            else:
                self.log.warn("Instructed to kill tasks but none were running")
        return killed_runs

    # def kill_selected_tasks(
    #     self, org_id: int, kill_list: list[ToBeKilled] = None
    # ) -> list[KilledRun]:
    #     """
    #     Kill tasks specified by a kill list, if they are currently running on
    #     this node

    #     Parameters
    #     ----------
    #     org_id: int
    #         The organization id of this node
    #     kill_list: list[ToBeKilled]
    #         A list of info about tasks that should be killed.

    #     Returns
    #     -------
    #     list[KilledRun]
    #         List with information on killed tasks
    #     """
    #     killed_list = []
    #     for container_to_kill in kill_list:
    #         if container_to_kill["organization_id"] != org_id:
    #             continue  # this run is on another node
    #         # find the task
    #         task = next(
    #             (
    #                 t
    #                 for t in self.active_tasks
    #                 if t.run_id == container_to_kill["run_id"]
    #             ),
    #             None,
    #         )
    #         if task:
    #             self.log.info(f"Killing containers for run_id={task.run_id}")
    #             self.active_tasks.remove(task)
    #             task.cleanup()
    #             killed_list.append(
    #                 KilledRun(
    #                     run_id=task.run_id,
    #                     task_id=task.task_id,
    #                     parent_id=task.parent_id,
    #                 )
    #             )
    #         else:
    #             self.log.warn(
    #                 "Received instruction to kill run_id="
    #                 f"{container_to_kill['run_id']}, but it was not "
    #                 "found running on this node."
    #             )
    #     return killed_list

    # def get_column_names(self, label: str, type_: str) -> list[str]:
    #     """
    #     Get column names from a node database

    #     Parameters
    #     ----------
    #     label: str
    #         Label of the database
    #     type_: str
    #         Type of the database

    #     Returns
    #     -------
    #     list[str]
    #         List of column names
    #     """
    #     pass


# TODO we need this code when we move to k8s clusters
# def create_volume(self, volume_name: str) -> None:
#     """
#     This method creates a persistent volume through volume claims. However, this method is not being
#     used yet, as using only host_path volume binds seems to be enough and more convenient
#     (see details on _create_volume_mounts) - this is to be discussed
#     """

#     """
#     @precondition: at least one persistent volume has been provisioned in the (single) kubernetes node

#     """

#     is_valid_vol_name = re.search(
#         "[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*",
#         volume_name,
#     )

#     if not is_valid_vol_name:
#         # TODO custom exceptions to decouple codebase from kubernetes
#         raise Exception(f"Invalid volume name; {volume_name}")

#     # create a persistent volume claim with the given name
#     pvc = client.V1PersistentVolumeClaim(
#         api_version="v1",
#         kind="PersistentVolumeClaim",
#         metadata=client.V1ObjectMeta(name=volume_name),
#         spec=client.V1PersistentVolumeClaimSpec(
#             storage_class_name="manual",
#             access_modes=["ReadWriteOnce"],
#             resources=client.V1ResourceRequirements(
#                 # TODO Storage quota to be defined in system properties
#                 requests={"storage": "1Gi"}
#             ),
#         ),
#     )

#     """
#     If the volume was not claimed with the given name yet, there won't be exception.
#     If the volume was already claimed with the same name, (which should not make the function to fail),
#         the API is expected to return an 409 error code.
#     """
#     try:
#         self.core_api.create_namespaced_persistent_volume_claim(self.task_namespace), body=pvc)
#     except client.rest.ApiException as e:
#         if e.status != 409:
#             # TODO custom exceptions to decouple codebase from kubernetes
#             raise Exception(
#                 f"Unexpected kubernetes API error code {e.status}"
#             ) from e
