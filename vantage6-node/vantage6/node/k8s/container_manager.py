import logging
import os
import re
import time
from pathlib import Path
from typing import List, NamedTuple, Tuple

import yaml
from kubernetes import client, config, watch
from kubernetes.client import V1EnvVar
from kubernetes.client.rest import ApiException

from vantage6.cli.context.node import NodeContext
from vantage6.common import logger_name
from vantage6.common.enum import AlgorithmStepType, RunStatus
from vantage6.node import globals
from vantage6.node.util import get_parent_id

# logging.basicConfig(level=logging.INFO)
# log = logging.getLogger(logger_name(__name__))


# Taken from docker_manager.py
class Result(NamedTuple):
    """
    Data class to store the result of the docker image.

    Attributes
    ----------
    run_id: int
        ID of the current algorithm run
    logs: str
        Logs attached to current algorithm run
    data: str
        Output data of the algorithm
    status_code: int
        Status code of the algorithm run
    """

    run_id: int
    task_id: int
    logs: str
    data: str
    status: str
    parent_id: int | None


# Taken from docker_manager.py
class ToBeKilled(NamedTuple):
    """Data class to store which tasks should be killed"""

    task_id: int
    run_id: int
    organization_id: int


# Taken from docker_manager.py
class KilledRun(NamedTuple):
    """Data class to store which algorithms have been killed"""

    run_id: int
    task_id: int
    parent_id: int


class ContainerManager:
    def __init__(self, ctx: NodeContext):
        self.log = logging.getLogger(logger_name(__name__))

        # v6-node configuration entries
        self.v6_config: dict

        self.running_on_pod: bool

        # Load v6-node configuration file
        with open(ctx.config_file, "r") as file:
            self.v6_config = yaml.safe_load(file)

        self.log.info(f"v6-K8S Node - loaded v6 settings:{self.v6_config}")

        # minik8s config, by default in the user's home directory root
        home_dir = os.path.expanduser("~")
        kube_config_file_path = os.path.join(home_dir, ".kube", "config")

        # Instanced within the host
        if os.path.exists(kube_config_file_path):
            self.running_on_pod = False
            # default microk8s config
            config.load_kube_config(kube_config_file_path)
            self.log.info(
                ">>> Loading K8S configuration file from the host filesystem (Node running on a regular host)"
            )
            # pprint.pp(self.v6_config)

        # Instanced within a pod
        elif os.path.exists(globals.KUBE_CONFIG_FILE_PATH):
            self.running_on_pod = True
            # Default mount location defined on POD configuration
            config.load_kube_config(globals.KUBE_CONFIG_FILE_PATH)
            self.log.info(
                ">>> Loading K8S configuration file from a hostPath volume (Node running within a POD)"
            )
        else:
            raise ValueError(
                "No K8S configuration file found. Node must be running within a POD or a host"
            )

        # before a task is executed it gets exposed to these policies
        self._policies = self._setup_policies(ctx.config)

        # K8S Batch API instance
        self.batch_api = client.BatchV1Api()
        # K8S Core API instance
        self.core_api = client.CoreV1Api()

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
        if not policies or not policies.get("allowed_algorithms"):
            self.log.warning(
                "No policies on allowed algorithms have been set for this node!"
            )
            self.log.warning(
                "This means that all algorithms are allowed to run on this node."
            )
        return policies

    # TODO add parameters "action" and "session_id"
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
    ) -> tuple[RunStatus, list[dict] | None]:
        """
        Checks if docker task is running. If not, creates DockerTaskManager to
        run the task

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
        RunStatus, list[dict] | None
            Returns a tuple with the status of the task and a description of
            each port on the VPN client that forwards traffic to the algorithm
            container (``None`` if VPN is not set up).
        """

        """
        Current V6 algorithm dispatch sequence:

            __start_task(task_incl_run)
                __docker.run(
                    ...
                     'docker_input' <- task_incl_run["input"]
                    ...
                )
                -->
                    task.run(
                        docker_input <- docker_input
                    )
                    -->
                        - Create input, output and token files: https://github.com/vantage6/vantage6/blob/3b38ac1e738a95cda1d78d90cc34f4f1190e9cdb/vantage6-node/vantage6/node/docker/task_manager.py#L428
                            - input: docker_input
                            - output: empty file
                            - token: token.encode("ascii")
                        - Set environment variables: https://github.com/vantage6/vantage6/blob/2a16890bde9abaf61cf134b00d8553ff5b5ce276/vantage6-node/vantage6/node/docker/task_manager.py#L477
                            "INPUT_FILE":
                            "OUTPUT_FILE":
                            "TOKEN_FILE":
                            "TEMPORARY_FOLDER":
                            "HOST": (proxy/server _host)
                            "PORT": (server port)
                            "API_PATH": ""

                            "USER_REQUESTED_DATABASE_LABELS"
                            "<LABEL>_DATABASE_URI"
                            "<LABEL>_DATABASE_TYPE"
                            "<LABEL>_DB_PARAM_<ADDITIONAL_PARAMETER>"
                        - Create and run an image container: https://github.com/vantage6/vantage6/blob/2a16890bde9abaf61cf134b00d8553ff5b5ce276/vantage6-node/vantage6/node/docker/task_manager.py#L344



        """
        # Usage context: https://github.com/vantage6/vantage6/blob/b0c961c8a060d9ea656e078e685a8e7d0560ef44/vantage6-node/vantage6/node/__init__.py#L349

        # Verify that an allowed image is used
        if not self.is_docker_image_allowed(image, task_info):
            msg = f"Docker image {image} is not allowed on this Node!"
            self.log.critical(msg)
            return RunStatus.NOT_ALLOWED, None

        # Check that this task is not already running
        if self.is_running(run_id):
            self.log.warning("Task is already being executed, discarding task")
            self.log.debug(f"run_id={run_id} is discarded")
            return RunStatus.ACTIVE, None

        str_task_id = str(task_info["id"])
        str_run_id = str(run_id)
        parent_id = str(get_parent_id(task_info))

        _io_related_env_variables: List[V1EnvVar]

        _volumes, _volume_mounts, _io_related_env_variables = (
            self._create_volume_mounts(
                run_id=str_run_id,
                docker_input=docker_input,
                token=token,
                databases_to_use=databases_to_use,
            )
        )

        # Setting the environment variables required by V6 algorithms.
        #   As these environment variables are used within the container/POD environment, file paths are relative
        #   to the mount paths (i.e., the container's file system) created by the method _crate_volume_mounts
        #
        env_vars: List[V1EnvVar] = [
            client.V1EnvVar(
                name="HOST",
                value=os.environ.get("PROXY_SERVER_HOST", globals.V6_NODE_FQDN),
            ),
            client.V1EnvVar(
                name="PORT",
                value=os.environ.get(
                    "PROXY_SERVER_PORT", str(globals.V6_NODE_PROXY_PORT)
                ),
            ),
            # TODO This environment variable correspond to the API PATH of the PROXY (not to be confused of the one of the
            # actual server). This variable should be eventually removed, as it is not being used to setup such PATH, so if
            # it is changed to a value different than empty, it leads to an error.
            client.V1EnvVar(name="API_PATH", value=""),
        ]

        env_vars.extend(_io_related_env_variables)

        container = client.V1Container(
            name=str_run_id,
            image=image,
            tty=True,
            volume_mounts=_volume_mounts,
            env=env_vars,
        )

        job_metadata = client.V1ObjectMeta(
            name=str_run_id,
            annotations={
                "run_id": str_run_id,
                "task_id": str_task_id,
                "task_parent_id": parent_id,
            },
        )

        # Define the job
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=job_metadata,
            spec=client.V1JobSpec(
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": str_run_id}),
                    spec=client.V1PodSpec(
                        containers=[container],
                        volumes=_volumes,
                        restart_policy="Never",
                    ),
                ),
                backoff_limit=3,
            ),
        )

        self.log.info(
            f"Creating namedspaced K8S job for task_id={str_task_id} and run_id={str_run_id}."
        )

        self.batch_api.create_namespaced_job(namespace="v6-jobs", body=job)

        # Based on
        # https://stackoverflow.com/questions/57563359/how-to-properly-update-the-status-of-a-job
        # https://kubernetes.io/docs/concepts/workloads/controllers/job/#pod-backoff-failure-policy

        """
        Pending, Running, Succeeded, Failed, Unknown
        Kubernetes will automatically retry the job N times (backoff_limit value above). According
        to the Pod's backoff failure policy, it will have a failed status only after the last failed retry.
        """

        interval = 1
        timeout = 60

        start_time = time.time()

        # the create_namespaced_job() method is asynchronous, so evaluating the pod execution status
        # requires first polling the K8S API until the new job/POD shows up.
        while True:
            pods = self.core_api.list_namespaced_pod(
                namespace="v6-jobs", label_selector=f"app={run_id}"
            )
            if pods.items:
                # The container was created. Now wait until it reports either an 'active' or 'failed' status
                # Pod-creation -> Pending -> Running -> Failed
                # What should be done in the case of a timeout while checking this?
                self.log.info(
                    f"{len(pods.items)} Job POD with label app={run_id} created successfuly on v6-jobs namespace. Waiting until it has a (k8S) running state."
                )
                status = self.__wait_until_pod_running(f"app={run_id}")
                self.log.info(
                    f"Job POD with label app={run_id} is now on a running state."
                )

                return status, None

            elif time.time() - start_time > timeout:
                self.log.error(
                    f"Timeoit while waiting Job POD with label app={run_id} to report a running state."
                )
                # The job could still start after the timeout
                return RunStatus.UNKNOWN_ERROR

            else:
                time.sleep(interval)

    def __wait_until_pod_running(self, run_id_label_selector: str) -> RunStatus:
        """
        This method execution gets blocked until the POD with the given label selector (which corresponds
        to the task's 'run_id') reports a 'Running' state. This method is expected to be used right
        after the job's creation request. Once this request is done, the POD has two initial statuses:
        'Pending' and then 'Running'.

        Returns:
        Either RunStatus.ACTIVE when the POD status is 'Running' (the POD container was kicked off),
                          or RunStatus.UNKNOWN_ERROR if there is a timeout while waiting for
                           reaching such 'Running' status (due to other errors)


        *Question: where are the failures detected on v6? : error code of command

        Wait for the POD to start
                                                              / Succeded
        Potential statuses of a Job POD: Pending -> Running - - Failed
                                                              \ Unknown
        """

        # Start watching for events on the pod
        w = watch.Watch()

        for event in w.stream(
            func=self.core_api.list_namespaced_pod,
            namespace="v6-jobs",
            label_selector=run_id_label_selector,
            timeout_seconds=120,
        ):
            pod_phase = event["object"].status.phase

            if pod_phase == "Running":
                w.stop()
                return RunStatus.ACTIVE

        # This point is reached after timeout
        return RunStatus.UNKNOWN_ERROR

    def _create_io_files(
        self,
        alg_input_file_path: str,
        docker_input: bytes,
        token_file_path: str,
        token: str,
        output_file_path: str,
    ):
        """
        Create the files required by the algorithms, which will be bound to the PODs through a volume mount:
        'docker_input' as the 'input' file, and 'token'
        """
        self.log.info(f"Creating {alg_input_file_path} and {token_file_path}")

        # Check if the files already exist
        # if Path(alg_input_file_path).exists() or Path(token_file_path).exists():
        #    raise Exception(f"Input file {alg_input_file_path} or Token file {token_file_path} already exist. Cannot overwrite.")

        # Create the directories if they don't exist (if there are no writing rights this will rise)
        alg_input_dir = Path(alg_input_file_path).parent
        token_dir = Path(token_file_path).parent
        output_dir = Path(token_file_path).parent

        alg_input_dir.mkdir(parents=True, exist_ok=True)
        token_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(alg_input_file_path, "wb") as alg_input_file:
            alg_input_file.write(docker_input)

        with open(token_file_path, "wb") as token_file:
            token_file.write(token.encode("ascii"))

        with open(output_file_path, "wb") as token_file:
            token_file.write(b"")

    def _create_volume_mounts(
        self, run_id: str, docker_input: bytes, token: str, databases_to_use: list[str]
    ) -> Tuple[List[client.V1Volume], List[client.V1VolumeMount], List[V1EnvVar]]:
        """
        Define all the mounts required by the algorithm/job: input files (csv), output, and temporal data

        Returns: a tuple with (1) the created volume names and their corresponding volume mounts and (2) the list
        of the environment variables required by the algorithms to use such mounts.

         Note: in the following Volume-claims could be used insted of 'host_path' volumes to decouple vantage6 file
          management from the storage provider (NFS, GCP, etc). However, persitent-volumes (from which
          volume-claims are be created), present a risk when used on local file systems. In particular,
          if two VC are created from the same PV, both would end sharing the same files.

          e.g. : Define the volume for temporal data
          tmp_volume = client.V1Volume(
            name=f'task-{str_run_id}-tmp',
            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name=tmp_vol_name)
          )

        """
        volumes: List[client.V1Volume] = []
        vol_mounts: List[client.V1VolumeMount] = []
        io_env_vars: List[V1EnvVar] = []

        # This method creates the folders required for the required tasks (subfolders
        # of the 'tasks-dir' defined in the v6 node configuration file), and then
        # bind these as host-volume mounts. The folder is created from the context
        # of the running node, so the target folder dependes on whether the node
        # is running from the host or from a POD.

        # If running whithin the POD, use the tas
        if self.running_on_pod:
            task_base_path = globals.TASK_FILES_ROOT
        # If running withn the host, use the value defined by the v6-config file
        else:
            task_base_path = self.v6_config["task_dir"]

        _input_file_path = os.path.join(task_base_path, run_id, "input")
        _token_file_path = os.path.join(task_base_path, run_id, "token")
        _output_file_path = os.path.join(task_base_path, run_id, "output")

        # Create algorithm's input and token files before creating volume mounts with them (relative to the node's file system: POD or host)
        self._create_io_files(
            alg_input_file_path=_input_file_path,
            docker_input=docker_input,
            token_file_path=_token_file_path,
            token=token,
            output_file_path=_output_file_path,
        )

        # Binding the required files and folders to the Job POD as HostPathVolume (using actual host path folder
        # as this is made by the K8S server).

        host_task_base_path = self.v6_config["task_dir"]

        _host_input_file_path = os.path.join(host_task_base_path, run_id, "input")
        _host_token_file_path = os.path.join(host_task_base_path, run_id, "token")
        _host_output_file_path = os.path.join(host_task_base_path, run_id, "output")
        _host_tmp_folder_path = os.path.join(host_task_base_path, run_id, "tmp")

        # Define a volume for input/output for this run. Following v6 convention, this is a volume bind to a
        # sub-folder created for the given run_id (i.e., the content will be shared by all the
        # algorithm instances of the same 'run' within this node).

        # Files or folders will be automatically created as described on https://kubernetes.io/docs/concepts/storage/volumes/#hostpath-volume-types

        ##### Volume for the output file (this creates an empty file)
        output_volume = client.V1Volume(
            name=f"task-{run_id}-output",
            host_path=client.V1HostPathVolumeSource(path=_host_output_file_path),
        )
        volumes.append(output_volume)
        # Volume mount path for i/o data (/app is the WORKDIR path of v6-node's container)
        output_volume_mount = client.V1VolumeMount(
            # standard containers volume mount location
            name=f"task-{run_id}-output",
            mount_path=globals.JOB_POD_OUTPUT_PATH,
        )

        vol_mounts.append(output_volume_mount)
        io_env_vars.append(
            client.V1EnvVar(name="OUTPUT_FILE", value=globals.JOB_POD_OUTPUT_PATH)
        )

        ##### Volume for the INPUT file (this creates an empty file, in which the input parameters user by the algorithm
        # will be written before starting the task.

        alg_input_volume = client.V1Volume(
            name=f"task-{run_id}-input",
            host_path=client.V1HostPathVolumeSource(path=_host_input_file_path),
        )
        volumes.append(alg_input_volume)

        alg_input_volume_mount = client.V1VolumeMount(
            # standard containers volume mount location
            name=f"task-{run_id}-input",
            mount_path=globals.JOB_POD_INPUT_PATH,
        )

        vol_mounts.append(alg_input_volume_mount)
        io_env_vars.append(
            client.V1EnvVar(name="INPUT_FILE", value=globals.JOB_POD_INPUT_PATH)
        )

        ####### Volume and volume mount for the TOKEN file. This creates an empty file first,
        # the Token should be written on it before launching the Job

        token_volume = client.V1Volume(
            name=f"token-{run_id}-input",
            host_path=client.V1HostPathVolumeSource(path=_host_token_file_path),
        )
        volumes.append(token_volume)

        token_volume_mount = client.V1VolumeMount(
            # standard containers volume mount location
            name=f"token-{run_id}-input",
            mount_path=globals.JOB_POD_TOKEN_PATH,
        )

        vol_mounts.append(token_volume_mount)
        io_env_vars.append(
            client.V1EnvVar(name="TOKEN_FILE", value=globals.JOB_POD_TOKEN_PATH)
        )

        ######## Volume for temporal data folder
        tmp_volume = client.V1Volume(
            name=f"task-{run_id}-tmp",
            host_path=client.V1HostPathVolumeSource(path=_host_tmp_folder_path),
        )

        volumes.append(tmp_volume)

        tmp_volume_mount = client.V1VolumeMount(
            # standard containers volume mount location
            name=f"task-{run_id}-tmp",
            mount_path=globals.JOB_POD_TMP_FOLDER_PATH,
        )

        vol_mounts.append(tmp_volume_mount)

        io_env_vars.append(
            client.V1EnvVar(
                name="TEMPORARY_FOLDER", value=globals.JOB_POD_TMP_FOLDER_PATH
            )
        )

        ##### Environment variable with the labels of the databases to be used
        labels_list = []
        for db in databases_to_use:
            labels_list.append(db["label"])
        labels_str = ",".join(labels_list)
        io_env_vars.append(
            client.V1EnvVar(name="USER_REQUESTED_DATABASE_LABELS", value="default")
        )
        # io_env_vars.append(client.V1EnvVar(name="USER_REQUESTED_DATABASE_LABELS", value=labels_str))

        # Bind-mounting all the CSV files (read only) defined on the configuration file
        # TODO bind other input data types
        # TODO include only the ones given in the 'databases_to_use parameter
        csv_input_files = list(
            filter(lambda o: (o["type"] == "csv"), self.v6_config["databases"])
        )

        for csv_input in csv_input_files:
            _volume = client.V1Volume(
                name=f"task-{run_id}-input-{csv_input['label']}",
                host_path=client.V1HostPathVolumeSource(csv_input["uri"]),
            )

            volumes.append(_volume)

            _volume_mount = client.V1VolumeMount(
                mount_path=f"/mnt/{csv_input['label']}",
                name=f"task-{run_id}-input-{csv_input['label']}",
                read_only=True,
            )

            vol_mounts.append(_volume_mount)

            io_env_vars.append(
                client.V1EnvVar(
                    name=f"{csv_input['label'].upper()}_DATABASE_URI",
                    value=f"/mnt/{csv_input['label']}",
                )
            )
            io_env_vars.append(
                client.V1EnvVar(
                    name=f"{csv_input['label'].upper()}_DATABASE_TYPE", value="csv"
                )
            )

        return volumes, vol_mounts, io_env_vars

    def create_volume(self, volume_name: str) -> None:
        """
        This method creates a persistent volume through volume claims. However, this method is not being
        used yet, as using only host_path volume binds seems to be enough and more convenient
        (see details on _create_volume_mounts) - this is to be discussed
        """

        """
        @precondition: at least one persistent volume has been provisioned in the (single) kubernetes node

        """

        is_valid_vol_name = re.search(
            "[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*",
            volume_name,
        )

        if not is_valid_vol_name:
            # TODO custom exceptions to decouple codebase from kubernetes
            raise Exception(f"Invalid volume name; {volume_name}")

        # create a persistent volume claim with the given name
        pvc = client.V1PersistentVolumeClaim(
            api_version="v1",
            kind="PersistentVolumeClaim",
            metadata=client.V1ObjectMeta(name=volume_name),
            spec=client.V1PersistentVolumeClaimSpec(
                storage_class_name="manual",
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(
                    # TODO Storage quota to be defined in system properties
                    requests={"storage": "1Gi"}
                ),
            ),
        )

        """
        If the volume was not claimed with the given name yet, there won't be exception.
        If the volume was already claimed with the same name, (which should not make the function to fail),
            the API is expected to return an 409 error code.
        """
        try:
            self.core_api.create_namespaced_persistent_volume_claim("v6-jobs", body=pvc)
        except client.rest.ApiException as e:
            if e.status != 409:
                # TODO custom exceptions to decouple codebase from kubernetes
                raise Exception(
                    f"Unexpected kubernetes API error code {e.status}"
                ) from e

    def _create_host_path_persistent_volume(self, path: str) -> None:
        """
        Programatically creates a persistent volume (in case it is needed for creating a
        volume claim). Just for reference, not currently being used.
        """
        pv = client.V1PersistentVolume(
            metadata=client.V1ObjectMeta(
                name="task-pv-volume", labels={"type": "local"}
            ),
            spec=client.V1PersistentVolumeSpec(
                storage_class_name="manual",
                capacity={"storage": "10Gi"},
                access_modes=["ReadWriteOnce"],
                host_path=client.V1HostPathVolumeSource(path=path),
            ),
        )
        self.core_api.create_persistent_volume(body=pv)

    def is_docker_image_allowed(self, docker_image_name: str, task_info: dict) -> bool:
        """
        Checks the docker image name.

        Against a list of regular expressions as defined in the configuration
        file. If no expressions are defined, all docker images are accepted.

        Parameters
        ----------
        docker_image_name: str
            uri to the docker image
        task_info: dict
            Dictionary with information about the task

        Returns
        -------
        bool
            Whether docker image is allowed or not
        """

        # TODO use original v6 implementation

        return True

    def is_running(self, run_id: int) -> bool:
        """

        Check if a container is already running for <run_id>.

        Parameters
        ----------
        run_id: int
            run_id of the algorithm container to be found

        Returns
        -------
        bool
            Whether or not algorithm container is running already
        """

        """
        To be discussed:
        Potential statuses of a Job POD: Pending, Running, Succeeded, Failed, Unknown
        This method is used locally to check whether a given task was already executed. In which case does
        happen?
        Given the above What would be the expected return value if the task was already completed or failed?

        """
        pods = self.core_api.list_namespaced_pod(
            namespace="v6-jobs", label_selector=f"app={run_id}"
        )
        if pods.items:
            return True
        else:
            return False

    def get_result(self) -> Result:
        """
        * Original description:
            Returns the oldest (FIFO) finished docker container.
            This is a blocking method until a finished container shows up. Once the
            container is obtained and the results are read, the container is
            removed from the docker environment.

        * Proposed (more accurate) description:
            proposed name: process_next_completed_job
            Process the next completed job (which can be either finsihed or failed), as soon any of these is shown (not necesarily FIFO):

                When failed-job found (after N attempts handled by kubernetes (N = job backoffLimit) ) =>
                    Cleanup POD/containers
                    return Result with:
                        RunStatus.CRASHED
                        Result: empty
                        Log error: Logs from the N pods (backoff limit)

                When Successful POD found =>
                    return Result with:
                        RunStatus.COMPLETED
                        Result: file content
                        Log: Logs from the N pods (backoff limit)


                                                              / Succeded
        Potential statuses of a Job POD: Pending -> Running - - Failed
                                                              \ Unknown

        """
        jobs = []

        # wait until there is at least one completed job available (successful or failed)
        # other statuses (pending/running/unknown) are ignored (for the moment)

        completed_job = False

        while not completed_job:
            jobs = self.batch_api.list_namespaced_job("v6-jobs")

            if not jobs:
                time.sleep(1)
            else:
                for job in jobs.items:
                    if job.status.succeeded:
                        job_id = job.metadata.name
                        self.log.info(
                            f"Found a completed job with a (k8s) Succeded status: {job_id}. Returning result with v6-COMPLETED status"
                        )

                        # get results by reading the output file created by the 'algorithm' container runned by the job (provisional convention: /output/avg.txt)
                        results = self.__get_job_result(job_id)

                        # get PODs logs
                        pod_tty_output = self.__get_job_pod_logs(
                            job_id=job_id, namespace="v6-jobs"
                        )

                        # destroy job and related POD(s)
                        self.log.info(
                            f"Cleaning up kubernetes Job {job.metadata.name} (job id = {job_id}) and related PODs"
                        )
                        self.batch_api.delete_namespaced_job(
                            name=job_id, namespace="v6-jobs"
                        )
                        self.__delete_job_related_pods(
                            job_id=job_id, namespace="v6-jobs"
                        )

                        self.log.info(
                            f"Sending results of run_id={job.metadata.annotations['run_id']} and task_id={job.metadata.annotations['task_id']} back to the server"
                        )

                        result = Result(
                            run_id=job.metadata.annotations["run_id"],
                            task_id=job.metadata.annotations["task_id"],
                            logs=pod_tty_output,
                            data=results,
                            status=RunStatus.COMPLETED,
                            parent_id=job.metadata.annotations["task_parent_id"],
                        )
                        completed_job = True

                    elif job.status.failed:
                        job_id = job.metadata.name

                        self.log.info(
                            f"Found a completed job with a (k8s) Failed status: {job.metadata.name} (job_id = {job_id}). Returning result with v6-CRASHED status"
                        )

                        # get PODs logs
                        pod_tty_output = self.__get_job_pod_logs(
                            job_id=job_id, namespace="v6-jobs"
                        )

                        # destroy POD
                        # Should the POD be cleaned up in this case too?
                        self.log.info(
                            f"Cleaning up container & job POD {job.metadata.name} / {job_id}"
                        )
                        self.batch_api.delete_namespaced_job(
                            name=job_id, namespace="v6-jobs"
                        )
                        self.__delete_job_related_pods(
                            job_id=job_id, namespace="v6-jobs"
                        )
                        self.log.info(
                            f"Sending failure details of run_id={job.metadata.annotations['run_id']} and task_id={job.metadata.annotations['task_id']} back to the server"
                        )
                        result = Result(
                            run_id=job.metadata.annotations["run_id"],
                            task_id=job.metadata.annotations["task_id"],
                            logs=pod_tty_output,
                            data=b"",
                            status=RunStatus.CRASHED,
                            parent_id=job.metadata.annotations["task_parent_id"],
                        )
                        completed_job = True

        return result

    def __get_job_result(self, job_id: str) -> bytes:
        """
        If executing the Node within a POD:
            TODO - define the convention of where the tasks folders are bind to the
                Node container filesystem

        #if executing from HOST, use path given in v6 config file
            #output_file = os.path.join(self.v6_config['task_dir'],run_id,'output')

        """
        if self.running_on_pod:
            # Running within a POD: use the standard tasks folder path mapped to the POD-container's file system.
            # @precondition:
            #  node_constants.TASK_FILES_ROOT is mapped to the path defined in the vantge6 configuration file (task_dir)
            succeded_job_output_file = os.path.join(
                globals.TASK_FILES_ROOT, job_id, "output"
            )
        else:
            # Running from the host (e.g., for testing purposes) - use the path defined in the configuration file
            succeded_job_output_file = os.path.join(
                self.v6_config["task_dir"], job_id, "output"
            )

        self.log.info(
            f"Reading data generated by job {job_id} at {succeded_job_output_file}"
        )
        with open(succeded_job_output_file, "rb") as fp:
            results = fp.read()
        return results

    def __get_job_pod_logs(self, job_id: str, namespace="v6-jobs") -> List[str]:
        """ "
        Get the logs generated by the PODs created by a job.

        If there are multiple PODs created by the job (e.g., due to multiple failed execution attempts -see
        backofflimit setting-) all the POD logs are merged as one.
        """

        pods_tty_logs = []

        job_selector = f"job-name={job_id}"
        job_pods_list = self.core_api.list_namespaced_pod(
            namespace, label_selector=job_selector
        )

        for job_pod in job_pods_list.items:
            self.log.info(
                f"Getting logs from POD {job_pod.metadata.name}, created by job {job_id}"
            )

            pod_log = self.core_api.read_namespaced_pod_log(
                name=job_pod.metadata.name, namespace="v6-jobs", _preload_content=True
            )

            pods_tty_logs.append(
                f"LOGS of POD {job_pod.metadata.name} (created by job {job_id}) \n {pod_log}"
            )

        return pods_tty_logs

    def __delete_job_related_pods(self, job_id, namespace="v6-job"):
        """
        Deletes all the PODs created by a Kubernetes job in a given namespace
        """
        job_selector = f"job-name={job_id}"
        job_pods_list = self.core_api.list_namespaced_pod(
            namespace, label_selector=job_selector
        )
        for job_pod in job_pods_list.items:
            try:
                self.log.info(f"Deleting pod {job_pod.metadata.name} of job {job_id}")
                self.core_api.delete_namespaced_pod(job_pod.metadata.name, namespace)
                self.log.info(f"Pod {job_pod.metadata.name} of job {job_id} deleted.")
            except ApiException:
                self.log.warn(
                    f"Warning: POD {job_pod.metadata.name} of job {job_id} couldn't be deleted."
                )

        # def cleanup_tasks(self) -> list[KilledRun]:
        """
        Stop all active tasks

        Returns
        -------
        list[KilledRun]:
            List of information on tasks that have been killed
        """

        # def cleanup(self) -> None:
        """
        Stop all active tasks and delete the isolated network

        Note: the temporary docker volumes are kept as they may still be used
        by a parent container
        """
        # note: the function `cleanup_tasks` returns a list of tasks that were
        # killed, but we don't register them as killed so they will be run
        # again when the node is restarted

        # def login_to_registries(self, registries: list = []) -> None:
        """
        Login to the docker registries

        Parameters
        ----------
        registries: list
            list of registries to login to
        """

        # def link_container_to_network(self, container_name: str, config_alias: str) -> None:
        """
        Link a docker container to the isolated docker network

        Parameters
        ----------
        container_name: str
            Name of the docker container to be linked to the network
        config_alias: str
            Alias of the docker container defined in the config file
        """

    # def kill_selected_tasks(
    #    self, org_id: int, kill_list: list[ToBeKilled] = None
    # ) -> list[KilledRun]:

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
        """

    def kill_selected_tasks(
        self, org_id: int, kill_list: list[ToBeKilled] = None
    ) -> list[KilledRun]:
        """
        Kill tasks specified by a kill list, if they are currently running on
        this node

        Parameters
        ----------
        org_id: int
            The organization id of this node
        kill_list: list[ToBeKilled]
            A list of info about tasks that should be killed.

        Returns
        -------
        list[KilledRun]
            List with information on killed tasks
        """
        """
        killed_list = []
        for container_to_kill in kill_list:
            if container_to_kill["organization_id"] != org_id:
                continue  # this run is on another node
            # find the task
            task = next(
                (
                    t
                    for t in self.active_tasks
                    if t.run_id == container_to_kill["run_id"]
                ),
                None,
            )
            if task:
                self.log.info(f"Killing containers for run_id={task.run_id}")
                self.active_tasks.remove(task)
                task.cleanup()
                killed_list.append(
                    KilledRun(
                        run_id=task.run_id,
                        task_id=task.task_id,
                        parent_id=task.parent_id,
                    )
                )
            else:
                self.log.warn(
                    "Received instruction to kill run_id="
                    f"{container_to_kill['run_id']}, but it was not "
                    "found running on this node."
                )
        return killed_list
        """

        # def get_column_names(self, label: str, type_: str) -> list[str]:
        """
        Get column names from a node database

        Parameters
        ----------
        label: str
            Label of the database
        type_: str
            Type of the database

        Returns
        -------
        list[str]
            List of column names
        """
