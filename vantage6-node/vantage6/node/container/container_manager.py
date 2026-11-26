import base64
import logging
import os
import re
import shutil
import threading
import time
from collections.abc import Callable
from itertools import groupby
from pathlib import Path

from socketio import Client as SocketIO

from vantage6.common import logger_name
from vantage6.common.client.node_client import NodeClient
from vantage6.common.dataclass import TaskDB
from vantage6.common.docker.addons import (
    get_digest,
    get_image_name_wo_tag,
)
from vantage6.common.enum import (
    AlgorithmStepType,
    DatabaseMountMode,
    RunStatus,
    TaskDatabaseType,
)
from vantage6.common.globals import (
    DATAFRAME_BETWEEN_GROUPS_SEPARATOR,
    DATAFRAME_WITHIN_GROUP_SEPARATOR,
    DEFAULT_DB_MOUNT_MODE,
    ENV_VAR_EQUALS_REPLACEMENT,
    SESSION_STATE_FILENAME,
    STRING_ENCODING,
    ContainerEnvNames,
    NodePolicy,
)
from vantage6.common.kubernetes.utils import database_env_label

from vantage6.cli.context.node import NodeContext

from vantage6.node.container.data_classes import KilledRun, Result, ToBeKilled
from vantage6.node.container.exceptions import (
    DataFrameNotFound,
    PermanentAlgorithmStartFail,
)
from vantage6.node.container.run_io import RunIO
from vantage6.node.enum import KillInitiator
from vantage6.node.globals import (
    DATABASE_BASE_PATH,
    DEFAULT_PROXY_PORT,
    ENV_VARS_NOT_SETTABLE_BY_NODE,
    TASK_FILES_ROOT,
    TASK_JOB_INPUT_PATH,
    TASK_JOB_OUTPUT_PATH,
    TASK_JOB_SESSION_FOLDER_PATH,
)
from vantage6.node.runtime import get_runtime
from vantage6.node.runtime.base import (
    ContainerRuntime,
    MountSpec,
    PullPolicy,
    RegistryCredentials,
    RunInfo,
    RunMetadata,
    RunSpec,
    RunState,
    StorageKind,
    StorageRef,
)
from vantage6.node.util import get_parent_id

TASK_STORAGE = StorageRef(StorageKind.TASK)


class ContainerManager:
    """
    Starts algorithm runs and processes their results, independent of the container
    platform. Everything platform specific is done by a ``ContainerRuntime``.
    """

    def __init__(
        self,
        ctx: NodeContext,
        client: NodeClient,
        runtime: ContainerRuntime | None = None,
    ):
        self.log = logging.getLogger(logger_name(__name__))
        self.ctx = ctx
        self.client = client
        self.socket_io = None
        self.runtime = runtime or get_runtime(ctx)

        self.databases = self._get_database_metadata()

        # before a task is executed it gets exposed to these policies
        self._policies = self._setup_policies(self.ctx.config)

        # whether to share or not algorithm logs with HQ
        self.share_algorithm_logs = self.ctx.config.get("share_algorithm_logs", True)
        if self.share_algorithm_logs:
            self.log.warning("Algorithm logs and errors will be shared with HQ.")

    def set_socket(self, socket_io: SocketIO) -> None:
        self.socket_io = socket_io

    @property
    def num_active_tasks(self) -> int:
        return sum(1 for run in self.runtime.list_runs() if not run.state.is_finished)

    def preflight(self) -> tuple[bool, str]:
        """Create the runtime's helper resources and check runs can be started."""
        self.runtime.prepare()
        return self.runtime.preflight()

    def validate_algorithm_isolation(self) -> tuple[bool, str]:
        """Verify that algorithm containers cannot reach the public internet."""
        return self.runtime.verify_isolation()

    def _get_pull_policy(self) -> PullPolicy:
        """
        Always pull the algorithm image (the default), unless the node policy allows
        a locally available image to be used.
        """
        require_algorithm_pull = self._policies.get(
            NodePolicy.REQUIRE_ALGORITHM_PULL.value, True
        )
        return (
            PullPolicy.ALWAYS if require_algorithm_pull else PullPolicy.IF_NOT_PRESENT
        )

    def _get_registries(self) -> list[RegistryCredentials]:
        return [
            RegistryCredentials(
                registry=reg["registry"],
                username=reg["username"],
                password=reg["password"],
            )
            for reg in self.ctx.config.get("private_docker_registries") or []
        ]

    def _get_database_metadata(self) -> dict[str, TaskDB]:
        """
        Collect the databases from the environment variables passed to the node.

        For every label in ``DATABASE_LABELS`` it reads ``DATABASE_<LABEL>_URI``,
        ``_TYPE`` and ``_MOUNT_MODE``. File and folder databases are found at
        ``DATABASE_BASE_PATH/<label>.<type>`` in the node container; where they are
        stored for algorithm containers is given by ``_CLAIM_NAME`` and
        ``_SUB_PATH`` (Kubernetes) or ``_HOST_PATH`` (Docker). All other
        ``DATABASE_<LABEL>_*`` variables are passed to data extraction algorithms.

        File databases in 'copy' mount mode are copied to the task storage, so that
        algorithms never get write access to the original file.
        """
        db_labels = [
            label.strip()
            for label in os.environ.get("DATABASE_LABELS", "").split(",")
            if label.strip()
        ]
        if not db_labels:
            self.log.warning("No databases found in the environment variables")
            return {}

        databases = {}
        for label in db_labels:
            env_label = database_env_label(label)
            prefix = f"DATABASE_{env_label}_"
            uri = os.environ.get(f"{prefix}URI", "")
            db_type = os.environ.get(f"{prefix}TYPE", "")

            mount_mode = os.environ.get(
                f"{prefix}MOUNT_MODE", DEFAULT_DB_MOUNT_MODE
            ).lower()
            if mount_mode not in DatabaseMountMode.list():
                raise ValueError(
                    f"Invalid mount_mode '{mount_mode}' for database '{label}'. "
                    f"Supported values are: {', '.join(DatabaseMountMode.list())}."
                )
            mount_mode = DatabaseMountMode(mount_mode)

            claim_name = os.environ.get(f"{prefix}CLAIM_NAME") or None
            sub_path = os.environ.get(f"{prefix}SUB_PATH", "")
            host_path = os.environ.get(f"{prefix}HOST_PATH") or None

            local_uri = uri
            tmp_uri = Path(DATABASE_BASE_PATH) / f"{label}.{db_type}"
            db_is_file = tmp_uri.exists() and tmp_uri.is_file()
            db_is_dir = tmp_uri.exists() and tmp_uri.is_dir()
            if db_is_file or db_is_dir:
                local_uri = str(tmp_uri)
                uri = uri or local_uri

            if db_is_file and mount_mode == DatabaseMountMode.COPY:
                # Algorithms get the copy in the task storage mounted instead
                claim_name = None
                host_path = None
                sub_path = self._copy_database_file(label, tmp_uri)

            storage_keys = {
                f"{prefix}{key}"
                for key in (
                    "URI",
                    "TYPE",
                    "MOUNT_MODE",
                    "CLAIM_NAME",
                    "SUB_PATH",
                    "HOST_PATH",
                )
            }
            env = {
                key.removeprefix(prefix): value
                for key, value in os.environ.items()
                if key.startswith(prefix) and key not in storage_keys
            }

            databases[label] = TaskDB(
                label=label,
                uri=uri,
                local_uri=local_uri,
                is_file=db_is_file,
                is_dir=db_is_dir,
                type=db_type,
                env=env,
                mount_mode=mount_mode,
                claim_name=claim_name,
                sub_path=sub_path,
                host_path=host_path,
            )

        self.log.debug("Databases: %s", databases)
        return databases

    def _copy_database_file(self, label: str, db_path: Path) -> str:
        """Copy a file database to the task storage; returns its path in there."""
        relative_path = Path("databases") / db_path.name
        copy_path = Path(TASK_FILES_ROOT) / relative_path
        copy_path.parent.mkdir(parents=True, exist_ok=True)
        self.log.info("Copying database '%s' to %s", label, copy_path)
        shutil.copy(db_path, copy_path)
        copy_path.chmod(0o666)
        return str(relative_path)

    @staticmethod
    def _database_mount(db: TaskDB) -> MountSpec:
        read_only = db.mount_mode == DatabaseMountMode.READ_ONLY
        if db.mount_mode == DatabaseMountMode.COPY and db.is_file:
            storage = TASK_STORAGE
        elif db.claim_name:
            storage = StorageRef(StorageKind.CLAIM, db.claim_name)
        elif db.host_path:
            storage = StorageRef(StorageKind.HOST_PATH, db.host_path)
        else:
            raise PermanentAlgorithmStartFail(
                f"Database '{db.label}' is a file or folder, but the node does not "
                "know where it is stored. Please restart the node with a node "
                "configuration that matches this node version."
            )
        return MountSpec(storage, db.sub_path or "", db.local_uri, read_only=read_only)

    def run(
        self,
        run_id: int,
        task_info: dict,
        image: str,
        function_arguments: bytes,
        session_id: int,
        token: str,
        databases_to_use: list[dict],
        action: AlgorithmStepType,
        on_status_change: Callable[[RunStatus], None],
    ) -> RunStatus:
        """
        Start an algorithm run.

        ``on_status_change`` is called with the statuses the run passes while it is
        being started, but not with the status that is returned.
        """
        init_org_id = task_info["init_org"]["id"]
        self.log.debug(
            "[Algorithm run %s - requested by org %s] Setting up algorithm run",
            run_id,
            init_org_id,
        )
        # In case we are dealing with a data-extraction or prediction task, we need to
        # know the dataframe that is being created or modified by the algorithm.
        df_details = task_info.get("dataframe", {})

        run_io = RunIO(
            run_id,
            session_id,
            action,
            self.client,
            df_details,
            task_dir_extension=self.ctx.config.get("dev", {}).get("task_dir_extension"),
        )

        if not self.is_image_allowed(image, task_info):
            self.log.critical(
                "[Algorithm run %s requested by org %s] Docker image %s is not allowed "
                "on this Node!",
                run_id,
                init_org_id,
                image,
            )
            return RunStatus.NOT_ALLOWED

        if self.is_running(run_io.container_name):
            self.log.warning(
                "[Algorithm run %s requested by org %s] Task is already being "
                "executed, discarding task",
                run_id,
                init_org_id,
            )
            return RunStatus.ACTIVE

        task_id = task_info["id"]
        parent_task_id = get_parent_id(task_info)

        try:
            mounts, env_vars, secrets = self._create_mounts(
                run_io=run_io,
                function_arguments=function_arguments,
                databases_to_use=databases_to_use,
            )
        except PermanentAlgorithmStartFail as e:
            self.log.warning(e)
            return RunStatus.FAILED
        except DataFrameNotFound as e:
            self.log.info(e)
            return RunStatus.DATAFRAME_NOT_FOUND
        except Exception:
            self.log.exception("Unknown error in creating volume mounts")
            return RunStatus.UNKNOWN_ERROR

        # Set environment variables for the algorithm client. This client is used
        # to communicate from the algorithm to HQ through the proxy.
        # The V6_PROXY_HOST env. variable is validated when the node is initialized
        env_vars[ContainerEnvNames.HOST.value] = os.environ.get("V6_PROXY_HOST")
        env_vars[ContainerEnvNames.PORT.value] = os.environ.get(
            "V6_PROXY_PORT", str(DEFAULT_PROXY_PORT)
        )

        if action == AlgorithmStepType.CENTRAL_COMPUTE:
            secrets[ContainerEnvNames.CONTAINER_TOKEN.value] = token

        self.log.debug(
            "[Algorithm run %s] Setting V6_PROXY_HOST=%s and V6_PROXY_PORT=%s env "
            "variables on the algorithm container",
            run_id,
            env_vars[ContainerEnvNames.HOST.value],
            env_vars[ContainerEnvNames.PORT.value],
        )

        env_vars[ContainerEnvNames.API_PATH.value] = ""
        env_vars[ContainerEnvNames.ALGORITHM_METHOD.value] = task_info["method"]
        env_vars[ContainerEnvNames.FUNCTION_ACTION.value] = action.value
        env_vars[ContainerEnvNames.TASK_ID.value] = str(task_id)
        env_vars[ContainerEnvNames.NODE_ID.value] = str(self.client.whoami.id_)
        env_vars[ContainerEnvNames.ORGANIZATION_ID.value] = str(
            self.client.whoami.organization_id
        )
        env_vars[ContainerEnvNames.COLLABORATION_ID.value] = str(
            self.client.collaboration_id
        )

        for key, value in self.ctx.config.get("algorithm_env", {}).items():
            if key in env_vars or key.upper() in env_vars:
                self.log.warning(
                    "[Algorithm run %s requested by org %s] Environment variable %s"
                    " is requested to be set as algorithm environment variable, but it "
                    "vantage6 infrastructure is already setting it.",
                    run_id,
                    init_org_id,
                    key,
                )
                self.log.warning(
                    "This will result in the algorithm not receiving the correct value,"
                    " which may result in unexpected behavior.",
                )
                continue
            env_vars[key] = value

        # Encode the environment variables to avoid issues with special characters
        env_vars = self._encode_environment_variables(env_vars)
        try:
            self._validate_environment_variables(env_vars)
            self._validate_environment_variables(secrets)
        except PermanentAlgorithmStartFail as e:
            self.log.warning(
                "[Algorithm run %s requested by org %s] Validation of environment "
                "variables failed: %s",
                run_id,
                init_org_id,
                e,
            )
            return RunStatus.FAILED

        spec = RunSpec(
            name=run_io.container_name,
            image=image,
            step=action,
            env=env_vars,
            secret_env=secrets,
            mounts=mounts,
            metadata=RunMetadata(
                run_id=run_io.run_id,
                task_id=task_id,
                task_parent_id=parent_task_id,
                init_org_id=init_org_id,
                action=action,
                session_id=session_id,
                df_name=df_details.get("name") if df_details else "",
                df_id=str(df_details.get("id")) if df_details else "",
                df_label=df_details.get("label") if df_details else "",
            ),
            pull_policy=self._get_pull_policy(),
            registries=self._get_registries(),
        )

        try:
            status = self.runtime.start_run(spec, on_status_change)
        except Exception:
            self.log.exception(
                "[Algorithm run %s requested by org %s] Could not start the algorithm",
                run_id,
                init_org_id,
            )
            self._remove_run(spec.name, run_id)
            return RunStatus.START_FAILED

        if status == RunStatus.ACTIVE:
            self._stream_logs(run_io=run_io)
        return status

    def _remove_run(self, name: str, run_id: int) -> None:
        try:
            self.runtime.remove_run(name, run_id)
        except Exception:
            self.log.exception("Could not remove the resources of run %s", run_id)

    def _stream_logs(self, run_io: RunIO) -> None:
        self.log.info(f"Starting thread to stream logs for run {run_io.run_id}")
        thread = threading.Thread(target=self.__log_stream, args=(run_io,))
        thread.start()

    def __log_stream(self, run_io: RunIO) -> None:
        if not self.share_algorithm_logs:
            self.log.info(
                "Algorithm logs will not be shared with HQ for run %s because "
                "share_algorithm_logs is disabled.",
                run_io.run_id,
            )
            return

        try:
            for log_line in self.runtime.stream_logs(run_io.container_name):
                self.socket_io.emit(
                    "algorithm_log",
                    {"run_id": run_io.run_id, "log": log_line},
                    namespace="/tasks",
                )
        except Exception as e:  # noqa: BLE001
            self.log.error(f"Error while streaming logs for run {run_io.run_id}: {e}")

    def _create_mounts(
        self,
        run_io: RunIO,
        function_arguments: bytes,
        databases_to_use: list[dict],
    ) -> tuple[list[MountSpec], dict[str, str], dict[str, str]]:
        """
        Create the input and output files of a run, and determine what the algorithm
        container mounts.

        Algorithm containers share the node's task storage, but only see the input
        and output file of their own run and the folder of their session.

        Returns
        -------
        tuple[list[MountSpec], dict[str, str], dict[str, str]]
            The mounts, the environment variables the algorithm needs to use them,
            and the secret environment variables.
        """
        # Paths relative to the root of the task storage
        input_file_path, output_file_path = run_io.create_files(function_arguments, b"")

        mounts = [
            MountSpec(TASK_STORAGE, output_file_path, TASK_JOB_OUTPUT_PATH),
            MountSpec(TASK_STORAGE, input_file_path, TASK_JOB_INPUT_PATH, True),
            MountSpec(
                TASK_STORAGE,
                run_io.session_file_manager.session_folder,
                TASK_JOB_SESSION_FOLDER_PATH,
            ),
        ]

        environment_variables = {
            ContainerEnvNames.OUTPUT_FILE.value: TASK_JOB_OUTPUT_PATH,
            ContainerEnvNames.INPUT_FILE.value: TASK_JOB_INPUT_PATH,
            ContainerEnvNames.SESSION_FOLDER.value: TASK_JOB_SESSION_FOLDER_PATH,
            ContainerEnvNames.SESSION_FILE.value: os.path.join(
                TASK_JOB_SESSION_FOLDER_PATH,
                run_io.session_file_manager.session_state_file_name,
            ),
        }

        # Sensitive environment variables
        secrets = {}

        if run_io.action == AlgorithmStepType.DATA_EXTRACTION:
            # A file or folder database is mounted; a service database must be
            # reachable from the container by its URI.
            self._validate_source_database(databases_to_use)
            source_database = databases_to_use[0]
            db: TaskDB = self.databases[source_database["label"]]
            if db.is_file or db.is_dir:
                if db.mount_mode == DatabaseMountMode.READ_ONLY:
                    self.log.info(
                        f"Binding database {source_database['label']} as read-only"
                    )
                elif db.is_file:
                    self.log.info(
                        f"Binding copy of database {source_database['label']} as "
                        "read-write"
                    )
                else:
                    self.log.info(
                        f"Binding database {source_database['label']} as read-write"
                    )
                mounts.append(self._database_mount(db))

            environment_variables[ContainerEnvNames.DATABASE_URI.value] = db.local_uri
            environment_variables[ContainerEnvNames.DATABASE_TYPE.value] = db.type

            # Read as {PREFIX}{KEY}=value by the `@source_database` decorator
            if db.env:
                for key in db.env:
                    env_key = f"{ContainerEnvNames.DB_PARAM_PREFIX.value}{key.upper()}"
                    secrets[env_key] = db.env[key]

        else:
            # Other steps work on dataframes of the session, which must exist
            self._validate_dataframes(databases_to_use, run_io)

            # group and sort on the position of the database in the argument list
            databases_to_use_sorted = sorted(
                databases_to_use, key=lambda x: x["position"]
            )
            grouped_databases = groupby(
                databases_to_use_sorted, key=lambda x: x["position"]
            )
            # Groups are separated by ';' and the dataframes are separated by ','
            environment_variables[ContainerEnvNames.USER_REQUESTED_DATAFRAMES.value] = (
                DATAFRAME_BETWEEN_GROUPS_SEPARATOR.join(
                    [
                        DATAFRAME_WITHIN_GROUP_SEPARATOR.join(
                            [db["dataframe_name"] for db in db_group]
                        )
                        for _, db_group in grouped_databases
                    ]
                )
            )

        return mounts, environment_variables, secrets

    def is_running(self, name: str) -> bool:
        """Whether the runtime already has a run with this container name."""
        return self.runtime.run_exists(name)

    def _run_io(self, run: RunInfo) -> RunIO:
        return RunIO.from_dict(
            run.metadata.to_dict(),
            self.client,
            task_dir_extension=self.ctx.config.get("dev", {}).get("task_dir_extension"),
        )

    def process_next_completed_run(self) -> Result:
        """
        Wait until an algorithm run has ended, and return its result.

        Blocks until there is a finished run. One run is processed per call.
        """
        self.log.info("Waiting for a completed run to process")
        while True:
            finished = [
                run for run in self.runtime.list_runs() if run.state.is_finished
            ]
            if finished:
                break
            time.sleep(1)

        run = finished[0]
        run_io = self._run_io(run)
        if run.state == RunState.SUCCEEDED:
            results, status = run_io.process_output()
        else:
            results, status = b"", RunStatus.CRASHED

        logs = self._get_logs(run)
        if run.reason:
            logs += f"\n\nAlgorithm container ended with reason: {run.reason}"

        self.log.info(
            "Sending results of run_id=%s and task_id=%s back to HQ",
            run.metadata.run_id,
            run.metadata.task_id,
        )
        result = Result(
            run_id=run.metadata.run_id,
            task_id=run.metadata.task_id,
            logs=logs,
            data=results,
            status=status,
            parent_id=run.metadata.task_parent_id,
            init_org_id=run.metadata.init_org_id,
        )
        self._remove_run(run.name, run.metadata.run_id)
        return result

    def _get_logs(self, run: RunInfo) -> str:
        try:
            return self.runtime.logs(run.name)
        except Exception as e:  # noqa: BLE001
            self.log.warning(f"Error while getting logs of {run.name}: {e}")
            return "error while getting logs"

    def cleanup(self) -> None:
        """Kill all algorithm runs and remove the runtime's helper resources."""
        self._kill_algorithm_runs(initiator=KillInitiator.NODE_SHUTDOWN)
        self.runtime.cleanup()

    def _kill_algorithm_runs(
        self,
        kill_list: list[ToBeKilled] | None = None,
        initiator: KillInitiator = KillInitiator.USER,
    ) -> list[KilledRun]:
        """
        Kill the runs in ``kill_list`` that run on this node, or all runs if no list
        is given.
        """
        run_ids_to_kill = None
        if kill_list:
            run_ids_to_kill = {
                to_kill.run_id
                for to_kill in kill_list
                if to_kill.organization_id == self.client.whoami.organization_id
            }
            if not run_ids_to_kill:
                return []

        runs = self.runtime.list_runs()
        if not runs:
            self.log.warning(
                "Received instructions to kill algorithms, but no runs found on this "
                "node",
            )
            return []

        killed_list: list[KilledRun] = []
        for run in runs:
            if run_ids_to_kill is None or run.metadata.run_id in run_ids_to_kill:
                killed_list.append(self._kill_run(run, initiator))

        if run_ids_to_kill:
            run_ids_killed = {r.run_id for r in killed_list}
            for run_id in run_ids_to_kill - run_ids_killed:
                self.log.warning(
                    "Received instruction to kill run_id=%s, but it was not found "
                    "running on this node.",
                    run_id,
                )

        return killed_list

    def _kill_run(self, run: RunInfo, initiator: KillInitiator) -> KilledRun:
        self.log.info("Killing run_id=%s", run.metadata.run_id)
        logs = self._get_logs(run)
        if initiator == KillInitiator.USER:
            logs += "\n\nAlgorithm was killed by user request."
        elif initiator == KillInitiator.NODE_SHUTDOWN:
            logs += "\n\nAlgorithm was killed because the node was shut down."
        self._remove_run(run.name, run.metadata.run_id)
        return KilledRun(
            run_id=run.metadata.run_id,
            task_id=run.metadata.task_id,
            parent_id=run.metadata.task_parent_id,
            logs=logs,
        )

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
        return config.get("policies") or {}

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
                TaskDatabaseType.DATAFRAME,
            )
            raise PermanentAlgorithmStartFail()

        # Validate that the requested dataframes exist. At this point they need to as
        # we are about to start the task.
        requested_dataframes = {db["dataframe_name"] for db in databases_to_use}
        available_dataframes = {
            file_.stem
            for file_ in Path(run_io.session_file_manager.local_session_folder).glob(
                "*.parquet"
            )
            if file_.stem != SESSION_STATE_FILENAME
        }
        # check that requested dataframes are a subset of available dataframes
        if requested_dataframes and not requested_dataframes.issubset(
            available_dataframes
        ):
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
            raise PermanentAlgorithmStartFail()

        source_database = databases_to_use[0]

        if source_database["type"] != TaskDatabaseType.SOURCE:
            self.log.error(
                "The database used in the data extraction step must be of type '%s'.",
                TaskDatabaseType.SOURCE,
            )
            ok = False

        if source_database["label"] not in self.databases:
            self.log.error(
                "The database used in the data extraction step does not exist."
            )
            ok = False

        if not ok:
            raise PermanentAlgorithmStartFail()

    def is_image_allowed(self, evaluated_img: str, task_info: dict) -> bool:
        """
        Checks that the (container) image name is allowed.

        Against a list of regular expressions as defined in the configuration file. If
        no expressions are defined, all container images are accepted.

        Parameters
        ----------
        evaluated_img: str
            URI of the image of which we are checking if it is allowed
        task_info: dict
            Dictionary with information about the task

        Returns
        -------
        bool
            Whether the image is allowed or not
        """
        # check if algorithm matches any of the regex cases
        allowed_algorithms = self._policies.get(NodePolicy.ALLOWED_ALGORITHMS.value)
        allowed_stores = self._policies.get(NodePolicy.ALLOWED_ALGORITHM_STORES.value)
        allow_either_whitelist_or_store = self._policies.get(
            "allow_either_whitelist_or_store", False
        )

        # check if user or their organization is allowed
        allowed_users = self._policies.get(NodePolicy.ALLOWED_USERS.value, [])
        allowed_orgs = self._policies.get(NodePolicy.ALLOWED_ORGANIZATIONS.value, [])
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
            except Exception as exc:  # noqa: BLE001
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
                    except Exception as exc:  # noqa: BLE001
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
                        digest_evaluated_image = get_digest(evaluated_img)
                        if not digest_evaluated_image:
                            self.log.warning(
                                "Could not obtain digest for image %s",
                                evaluated_img,
                            )
                        digest_policy_image = get_digest(allowed_algo)
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
            except Exception:  # noqa: BLE001
                store_id = None
            if store_id:
                store_info = self.client.algorithm_store.get(store_id)
                store_from_task = store_info["url"]
                # check if the store matches any of the regex cases
                if isinstance(allowed_stores, str):
                    allowed_stores = [allowed_stores]
                store_url_whitelisted = False
                for allowed_store in allowed_stores:
                    if not self._is_regex_pattern(allowed_store):
                        # check if string matches exactly
                        if allowed_store == store_from_task:
                            store_url_whitelisted = True
                    else:
                        expr_ = re.compile(allowed_store)
                        if expr_.match(store_from_task):
                            store_url_whitelisted = True

                if store_url_whitelisted:
                    # The store's URL is whitelisted, but that alone does not prove
                    # that the evaluated image is actually a registered, approved
                    # algorithm in that store - HQ is the one asserting that
                    # association, and HQ is not fully trusted here. Re-verify
                    # directly with the store itself instead of trusting HQ's claim.
                    #
                    # If the store is registered under a `localhost` URL (dev env)
                    # translate it to an address reachable from inside this pod
                    reachable_store_url = self.runtime.host_reachable_url(
                        store_info["url"]
                    )
                    self.client.algorithm_store.url = (
                        f"{reachable_store_url}{store_info['api_path']}"
                    )
                    self.client.algorithm_store.store_id = store_id
                    self.client.algorithm_store.uses_hq_keycloak = bool(
                        store_info.get("uses_hq_keycloak")
                    )
                    algorithm = self.client.algorithm_store.get_algorithm(evaluated_img)
                    if algorithm:
                        store_whitelisted = True
                    else:
                        self.log.warning(
                            "Algorithm store %s did not confirm that image %s is a "
                            "registered, approved algorithm there. Denying the "
                            "allowed_algorithm_stores policy for this image. This "
                            "can also happen if the algorithm store does not yet "
                            "support node verification requests.",
                            store_from_task,
                            evaluated_img,
                        )

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
        # https://github.com/corydolphin/flask-cors/blob/a5003f391e56f74f11a3e509cd180787c75eb6b0/flask_cors/core.py#L266
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
        ]
        # Use common characters used in regular expressions as a proxy
        # for if this string is in fact a regex.
        return any(c in pattern for c in common_regex_chars)

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

    def kill_algorithm_runs(
        self, kill_list: list[ToBeKilled] | None = None
    ) -> list[KilledRun]:
        """
        Kill algorithm runs currently running on this node.

        Parameters
        ----------
        kill_list: list[ToBeKilled] (optional)
            A list of info on tasks that should be killed. If the list
            is not specified, all running algorithm containers will be killed.

        Returns
        -------
        list[KilledRun]
            List of dictionaries with information on killed tasks
        """
        if not kill_list:
            self.log.warning(
                "Received instruction to kill all algorithms running on this "
                "node. Executing that now..."
            )

        killed_runs = self._kill_algorithm_runs(kill_list=kill_list)

        if len(killed_runs) > 0:
            self.log.warning(
                "Killed the following run ids as instructed via socket: %s",
                ", ".join([str(r.run_id) for r in killed_runs]),
            )
        else:
            self.log.warning("Instructed to kill tasks but none were running")

        return killed_runs
