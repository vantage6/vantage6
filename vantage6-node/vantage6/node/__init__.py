"""
The vantage6 node's core function is to retrieve tasks from the central server, run them
and return the results.

The node application runs four threads:

*Main thread*
    Checks the task queue and run the next task if there is one available.
*Listening thread*
    Listens for incoming websocket messages. Among other functionality, it adds
    new tasks to the task queue.
*Speaking thread*
    Waits for tasks to finish. When they do, return the results to the central
    server.
*Proxy server thread*
    Algorithm containers are isolated from the internet for security reasons.
    The local proxy server provides an interface to the central server for
    algorithm containers to create subtasks and retrieve their results.

The node connects to the server using a websocket connection. This connection
is mainly used for sharing status updates. This avoids the need for polling to
see if there are new tasks available.
"""

import datetime
import importlib.metadata
import json
import logging
import os
import queue
import sys
import threading
import time
from pathlib import Path
from threading import Thread

import psutil
import pynvml
import requests.exceptions
from gevent.pywsgi import WSGIServer
from keycloak import KeycloakAuthenticationError
from socketio import Client as SocketIO

from vantage6.common import logger_name, validate_required_env_vars
from vantage6.common.client.node_client import NodeClient
from vantage6.common.enum import AlgorithmStepType, RunStatus, TaskStatusQueryOptions
from vantage6.common.globals import (
    PING_INTERVAL_SECONDS,
    NodeConfigKey,
    NodePolicy,
    RequiredNodeEnvVars,
)
from vantage6.common.log import get_file_logger

from vantage6.cli.context.node import NodeContext

from vantage6.node import proxy_server
from vantage6.node.globals import (
    SLEEP_BTWN_NODE_LOGIN_TRIES,
    TIME_LIMIT_INITIAL_CONNECTION_WEBSOCKET,
    TIME_LIMIT_RETRY_CONNECT_NODE,
)
from vantage6.node.k8s.container_manager import ContainerManager
from vantage6.node.k8s.data_classes import ToBeKilled
from vantage6.node.socket import NodeTaskNamespace
from vantage6.node.util import get_parent_id

__version__ = importlib.metadata.version(__package__)


# ------------------------------------------------------------------------------
class Node:
    """
    Authenticates to the central server, setup encryption, a
    websocket connection, retrieving task that were posted while
    offline, preparing dataset for usage and finally setup a
    local proxy server..

    Parameters
    ----------
    ctx: NodeContext
        Application context object.

    """

    def __init__(self, ctx: NodeContext):
        self.log = logging.getLogger(logger_name(__name__))
        self.ctx = ctx
        self.gpu_metadata_available = True

        # validate that the required environment variables are set
        validate_required_env_vars(RequiredNodeEnvVars)

        # Initialize the node. If it crashes, shut down the parts that started
        # already
        try:
            self.initialize()
        except Exception:
            self.cleanup()
            raise

    def initialize(self) -> None:
        """Initialization of the node"""

        self.config = self.ctx.config
        self.debug: dict = self.config.get("debug", {})

        self._using_encryption = None

        # initialize Node connection to the server
        self.client = self._setup_node_client(self.config)

        self.k8s_container_manager = ContainerManager(self.ctx, self.client)

        # ensure that the namespace to create tasks in is set up correctly or try to
        # create it
        self.log.debug("Ensuring that the task namespace is properly configured")
        namespace_created = self.k8s_container_manager.ensure_task_namespace()
        if not namespace_created:
            self.log.error("Could not create the task namespace. Exiting.")
            exit(1)

        self.log.info("Connecting server: %s", self.client.server_url)

        # Authenticate with the server, obtaining a JSON Web Token.
        # Note that self.authenticate() blocks until it succeeds.
        self.runs_queue = queue.Queue()
        self.log.debug("Authenticating")
        self.authenticate()

        # Setup encryption
        self.setup_encryption()

        # Thread for proxy server for algorithm containers, so they can
        # communicate with the central server.
        self.log.info("Setting up proxy server")
        t = Thread(target=self.__proxy_server_worker, daemon=True)
        t.start()

        # Create a long-lasting websocket connection.
        self.log.debug("Creating websocket connection with the server")
        self.connect_to_socket()

        self.start_processing_threads()

        # TODO reactivate this after redoing docker-specific implementation (issue
        # https://github.com/vantage6/vantage6/issues/2080)
        # self.log.debug("Start thread for sending system metadata")
        # t = Thread(target=self.__metadata_worker, daemon=True)
        # t.start()

        self.log.info("Init complete")

    def _setup_node_client(self, config: dict) -> NodeClient:
        return NodeClient(
            server_url=(
                f"{config.get('server_url')}:{config.get('port')}"
                f"{config.get('api_path')}"
            ),
            auth_url=os.environ.get(RequiredNodeEnvVars.KEYCLOAK_URL.value),
            node_account_name=os.environ.get(RequiredNodeEnvVars.V6_NODE_NAME.value),
            api_key=os.environ.get(RequiredNodeEnvVars.V6_API_KEY.value),
        )

    def __metadata_worker(self) -> None:
        """
        Periodically send system metadata to the server.
        """
        if not self.config.get("prometheus", {}).get("enabled", False):
            self.log.info("Prometheus is not enabled, skipping metadata worker")
            return

        report_interval = self.config.get("prometheus", {}).get(
            "report_interval_seconds", 45
        )

        while True:
            try:
                metadata = self.__gather_system_metadata()
                self.socketIO.emit("node_metrics_update", metadata, namespace="/tasks")
            except Exception:
                self.log.exception("Metadata thread had an exception")
            time.sleep(report_interval)

    def __gather_system_metadata(self) -> dict:
        """
        Gather system metadata such as CPU, memory, OS, and GPU information.

        Returns
        -------
        dict
            Dictionary containing system metadata.
        """
        metadata = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "num_algorithm_containers": len(self.__docker.active_tasks),
            "os": os.name,
            "platform": sys.platform,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
        }

        if self.gpu_metadata_available:
            gpu_metadata = self.__gather_gpu_metadata()
            if gpu_metadata:
                metadata.update(gpu_metadata)

        return metadata

    def __gather_gpu_metadata(self) -> dict | None:
        """
        Gather GPU metadata such as GPU name, load, memory usage, and temperature.

        Returns
        -------
        dict
            Dictionary containing GPU-related metrics.
        """

        try:
            pynvml.nvmlInit()
            gpu_count = pynvml.nvmlDeviceGetCount()

            gpu_metadata = {
                "gpu_count": gpu_count,
                "gpu_load": [],
                "gpu_memory_used": [],
                "gpu_memory_free": [],
                "gpu_temperature": [],
            }

            for i in range(gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                gpu_metadata["gpu_load"].append(
                    pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                )
                gpu_metadata["gpu_memory_used"].append(
                    pynvml.nvmlDeviceGetMemoryInfo(handle).used
                )
                gpu_metadata["gpu_memory_free"].append(
                    pynvml.nvmlDeviceGetMemoryInfo(handle).free
                )
                gpu_metadata["gpu_temperature"].append(
                    pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                )
            pynvml.nvmlShutdown()
            return gpu_metadata
        except pynvml.NVMLError as e:
            self.log.warning(f"Failed to gather GPU metadata: {e}")
            self.gpu_metadata_available = False
            return None

    def __proxy_server_worker(self) -> None:
        """
        Proxy algorithm container communcation.

        A proxy for communication between algorithms and central
        server.
        """

        # The PROXY_SERVER_HOST is required for the node to work. There are no default
        # values for it as its value (a FQDN) depends on the namespace where the
        # K8S-service with the node is running.
        if "PROXY_SERVER_HOST" in os.environ:
            proxy_host = os.environ.get("PROXY_SERVER_HOST")
            os.environ["PROXY_SERVER_HOST"] = proxy_host
        else:
            self.log.error(
                "The environment variable PROXY_SERVER_HOST, required to start the Node's proxy-server is not set"
            )
            self.log.info("Shutting down the node...")
            exit(1)

        # 'app' is defined in vantage6.node.proxy_server
        debug_mode = self.debug.get("proxy_server", False)
        if debug_mode:
            self.log.debug("Debug mode enabled for proxy server")
            proxy_server.app.debug = True
        proxy_server.app.config["SERVER_IO"] = self.client

        # The value on the module variable 'server_url' defines the target of the
        # 'make_request' method.
        proxy_server.server_url = self.client.server_url
        self.log.info(
            "Setting target endpoint for the algorithm's client as : %s",
            proxy_server.server_url,
        )

        # set up proxy server logging
        Path(self.ctx.proxy_log_file).parent.mkdir(parents=True, exist_ok=True)
        log_level = getattr(logging, self.config["logging"]["level"].upper())
        self.proxy_log = get_file_logger(
            "proxy_server", self.ctx.proxy_log_file, log_level_file=log_level
        )

        # proxy port set on the node configuration file
        node_proxy_port = int(self.config.get("node_proxy_port"))

        self.log.info("Starting proxyserver at '%s:%s'", proxy_host, node_proxy_port)
        http_server = WSGIServer(
            ("0.0.0.0", node_proxy_port), proxy_server.app, log=self.proxy_log
        )

        try:
            os.environ["PROXY_SERVER_PORT"] = str(node_proxy_port)
            http_server.serve_forever()

        except OSError as e:
            self.log.error(
                "Error while trying to start the proxy server at %s:%s",
                proxy_host,
                node_proxy_port,
            )
            self.log.info(
                "Check that port %s is not being used by another process.",
                node_proxy_port,
            )
            self.log.info("%s: %s", type(e), e)
            self.log.info("Shutting down the node...")
            exit(1)

    def sync_task_queue_with_server(self) -> None:
        """Get all unprocessed tasks from the server for this node."""
        assert self.client.cryptor, "Encrpytion has not been setup"

        # request open tasks from the server
        runs_to_execute = self.client.run.list(
            state=TaskStatusQueryOptions.OPEN.value, include_task=True
        )

        # add the tasks to the queue
        self.__add_task_runs_to_queue(runs_to_execute)
        self.log.info("Received %s tasks", self.runs_queue._qsize())

    def get_task_and_add_to_queue(self, task_id: int) -> None:
        """
        Fetches (open) task with task_id from the server. The `task_id` is
        delivered by the websocket-connection.

        Parameters
        ----------
        task_id : int
            Task identifier
        """
        # fetch open algorithm runs for this node
        runs_to_execute = self.client.run.list(
            include_task=True, state=TaskStatusQueryOptions.OPEN.value, task_id=task_id
        )

        # add the tasks to the queue
        self.__add_task_runs_to_queue(runs_to_execute)

    def __add_task_runs_to_queue(self, runs_to_execute: list[dict]) -> None:
        """
        Add a task to the queue.

        Parameters
        ----------
        taskresult : list[dict]
            A list of dictionaries with information required to run the
            algorithm
        """
        for run_to_execute in runs_to_execute:
            try:
                if not self.k8s_container_manager.is_running(run_to_execute["id"]):
                    self.runs_queue.put(run_to_execute)
                else:
                    self.log.info(
                        "Not starting task %s - %s as it is already running",
                        run_to_execute["task"]["id"],
                        run_to_execute["task"]["name"],
                    )
            except Exception:
                self.log.exception("Error while syncing task queue")

    def __start_task(self, run_to_execute: dict) -> None:
        """
        Start the docker image and notify the server that the task has been
        started.

        Parameters
        ----------
        run_to_execute : dict
            A dictionary with information required to run the algorithm
        """
        task = run_to_execute["task"]
        self.log.info("Starting task %s - %s", task["id"], task["name"])

        # notify that we are processing this task
        run_id = run_to_execute["id"]

        self.client.set_run_start_time(run_id)

        # each algorithm container has its own purpose annotated by the action
        try:
            container_action = AlgorithmStepType(run_to_execute["action"])
        except ValueError:
            self.log.error(
                "Unrecognized action %s. Cancelling task.", run_to_execute["action"]
            )
            self.client.run.patch(
                id_=run_id,
                data={
                    "status": RunStatus.FAILED.value,
                    "finished_at": datetime.datetime.now().isoformat(),
                    "log": f"Unrecognized action {run_to_execute['action']}",
                },
            )
            self.__emit_algorithm_status_change(task, run_to_execute, RunStatus.FAILED)
            return

        # Only compute containers need a token as they are the only ones that should
        # create subtasks
        token = ""
        if container_action == AlgorithmStepType.CENTRAL_COMPUTE:
            token = self.client.request_token_for_container(task["id"], task["image"])
            try:
                token = token["container_token"]
            except KeyError:
                # if a token could not be generated, this is a sign that task is already
                # finished. To prevent this from happening every time node is restarted,
                # patch the node to failed
                self.log.error(
                    "Container token could not be obtained: %s", token.get("msg")
                )
                self.client.run.patch(
                    id_=run_id,
                    data={
                        "status": RunStatus.FAILED.value,
                        "log": "Could not obtain algorithm container token",
                    },
                )

        # Run the container. This adds the created container/task to the list
        # __docker.active_tasks
        run_status: RunStatus = self.k8s_container_manager.run(
            action=container_action,
            run_id=run_id,
            task_info=task,
            image=task["image"],
            function_arguments=run_to_execute["arguments"],
            session_id=task["session"]["id"],
            token=token,
            databases_to_use=task.get("databases", []),
        )

        # save task status to the server
        update = {"status": run_status.value}
        if run_status == RunStatus.NOT_ALLOWED:
            # set finished_at to now, so that the task is not picked up again
            # (as the task is not started at all, unlike other crashes, it will
            # never finish and hence not be set to finished)
            update["finished_at"] = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
        self.client.run.patch(id_=run_id, data=update)

        # send socket event to alert everyone of task status change. In case the
        # namespace is not connected, the socket notification will not be sent to other
        # nodes, but the task will still be processed
        self.__emit_algorithm_status_change(task, run_id, run_status)

    def __emit_algorithm_status_change(
        self, task: dict, run_id: int, status: RunStatus
    ) -> None:
        """
        Emit a socket event to alert everyone of task status change.

        Parameters
        ----------
        task_id : dict
            Task metadata
        run_id : int
            Run ID
        status : RunStatus
            Status of the algorithm run
        """
        # ensure that the /tasks namespace is connected. This may take a while
        # (usually < 5s) when the socket just (re)connected
        MAX_ATTEMPTS = 30
        retries = 0
        while "/tasks" not in self.socketIO.namespaces and retries < MAX_ATTEMPTS:
            retries += 1
            self.log.debug("Waiting for /tasks namespace to connect...")
            time.sleep(1)
        self.log.debug("Connected to /tasks namespace")

        self.socketIO.emit(
            "algorithm_status_change",
            data={
                "node_id": self.client.whoami.id_,
                "status": status.value,
                "run_id": run_id,
                "task_id": task["id"],
                "collaboration_id": self.client.collaboration_id,
                "organization_id": self.client.whoami.organization_id,
                "parent_id": get_parent_id(task),
            },
            namespace="/tasks",
        )

    def __poll_task_results(self) -> None:
        """
        Sending messages to central server.

        Routine that is in a seperate thread sending results
        to the server when they come available.
        """
        # TODO change to a single request, might need to reconsider
        #     the flow
        self.log.debug("Waiting for results to send to the server")

        while True:
            try:
                results = self.k8s_container_manager.process_next_completed_job()
                self.log.info(f"Sending result (run={results.run_id}) to the server!")

                # FIXME: why are we retrieving the result *again*? Shouldn't we
                # just store the task_id when retrieving the task the first
                # time?
                response = self.client.request(f"run/{results.run_id}")
                task_id = response.get("task", {}).get("id")

                if not task_id:
                    self.log.error(
                        "Task id for run id=%s could not be retrieved", results.run_id
                    )
                    return

                response = self.client.request(f"task/{task_id}")

                init_org = response.get("init_org")
                if not init_org:
                    self.log.error(
                        "Initiator organization from task (id=%s) could not be "
                        "retrieved!",
                        task_id,
                    )

                self.client.run.patch(
                    id_=results.run_id,
                    data={
                        "result": results.data,
                        "log": results.logs,
                        "status": results.status.value,
                        "finished_at": datetime.datetime.now().isoformat(),
                    },
                    init_org_id=init_org.get("id"),
                )

                # notify other nodes, server and clients about algorithm status
                # change
                self.socketIO.emit(
                    "algorithm_status_change",
                    data={
                        "node_id": self.client.whoami.id_,
                        "status": results.status.value,
                        "run_id": results.run_id,
                        "task_id": results.task_id,
                        "collaboration_id": self.client.collaboration_id,
                        "organization_id": self.client.whoami.organization_id,
                        "parent_id": results.parent_id,
                    },
                    namespace="/tasks",
                )
            except Exception as e:
                self.log.exception(
                    "poll_task_results (Speaking) thread had an exception: %s - %s",
                    type(e).__name__,
                    e,
                )

            time.sleep(1)

    def __print_connection_error_logs(self):
        """Print error message when node cannot find the server"""
        self.log.warning("Could not connect to the server. Retrying in 10 seconds")
        self.log.info(
            "Are you sure the server can be reached at %s?", self.client.server_url
        )

    def authenticate(self) -> None:
        """
        Authenticate with the server using the api-key from the configuration
        file. If the server rejects for any reason -other than a wrong API key-
        serveral attempts are taken to retry.
        """

        success = False
        i = 0
        while i < TIME_LIMIT_RETRY_CONNECT_NODE / SLEEP_BTWN_NODE_LOGIN_TRIES:
            i = i + 1
            try:
                self.client.authenticate()

            except KeycloakAuthenticationError as e:
                msg = "Authentication failed: API key or node name is wrong!"
                self.log.warning(msg)
                self.log.warning(e)
                break
            except requests.exceptions.ConnectionError:
                self.__print_connection_error_logs()
                time.sleep(SLEEP_BTWN_NODE_LOGIN_TRIES)
            except Exception as e:
                msg = (
                    "Authentication failed. Retrying in "
                    f"{SLEEP_BTWN_NODE_LOGIN_TRIES} seconds!"
                )
                self.log.warning(msg)
                self.log.warning(e)
                time.sleep(SLEEP_BTWN_NODE_LOGIN_TRIES)

            else:
                # This is only executed if try-block executed without error.
                success = True
                break

        if success:
            self.log.info("Node '%s' authenticated successfully", self.client.name)
        else:
            self.log.critical("Unable to authenticate. Exiting")
            exit(1)

        # start thread to keep the connection alive by refreshing the token
        self.client.auto_renew_token()

    def private_key_filename(self) -> Path:
        """Get the path to the private key."""

        # FIXME: Code duplication: vantage6/cli/node.py uses a lot of the same
        #   logic. Suggest moving this to ctx.get_private_key()
        filename = self.config["encryption"]["private_key"]

        # filename may be set to an empty string
        if not filename:
            filename = "private_key.pem"

        # If we're running dockerized, the location may have been overridden
        filename = os.environ.get("PRIVATE_KEY", filename)

        # If ctx.get_data_file() receives an absolute path, its returned as-is
        fullpath = Path(self.ctx.get_data_file(filename))

        return fullpath

    def setup_encryption(self) -> None:
        """
        Setup encryption for the node if it is part of an encrypted collaboration.

        This uses the private key file that is specified in the node configuration.
        """
        encrypted_collaboration = self.client.is_encrypted_collaboration()
        encrypted_node = self.config["encryption"]["enabled"]

        if encrypted_collaboration != encrypted_node:
            # You can't force it if it just ain't right, you know?
            raise Exception("Expectations on encryption don't match?!")

        if encrypted_collaboration:
            self.log.warning("Enabling encryption!")
            # TODO (HC) check that encryption works with k8s-based node
            private_key_file = self.private_key_filename()
            self.client.setup_encryption(private_key_file)

        else:
            self.log.warning("Disabling encryption!")
            self.client.setup_encryption(None)

    def connect_to_socket(self) -> None:
        """
        Create long-lasting websocket connection with the server. The
        connection is used to receive status updates, such as new tasks.
        """
        debug_mode = self.debug.get("socketio", False)
        if debug_mode:
            self.log.debug("Debug mode enabled for socketio")
        self.socketIO = SocketIO(
            request_timeout=60, logger=debug_mode, engineio_logger=debug_mode
        )

        self.socketIO.register_namespace(NodeTaskNamespace("/tasks"))
        NodeTaskNamespace.node_worker_ref = self

        self.socketIO.connect(
            url=self.client.server_url,
            headers=self.client.headers,
            wait=False,
        )

        # Log the outcome
        i = 0
        while not self.socketIO.connected:
            if i > TIME_LIMIT_INITIAL_CONNECTION_WEBSOCKET:
                self.log.critical(
                    "Could not connect to the websocket channels, do you have a "
                    "slow connection?"
                )
                exit(1)
            self.log.debug("Waiting for socket connection...")
            time.sleep(1)
            i += 1

        self.log.info("Connected to server at %s", self.client.server_url)

        self.log.debug(
            "Starting thread to ping the server to notify this node is online."
        )
        self.socketIO.start_background_task(self.__socket_ping_worker)

    def __socket_ping_worker(self) -> None:
        """
        Send ping messages periodically to the server over the socketIO
        connection to notify the server that this node is online
        """
        # Wait for the socket to be connected to the namespaces on startup
        time.sleep(5)

        while True:
            try:
                if self.socketIO.connected:
                    self.socketIO.emit("ping", namespace="/tasks")
                else:
                    self.log.debug("SocketIO is not connected, skipping ping")
            except Exception:
                self.log.exception("Ping thread had an exception")
            # Wait before sending next ping
            time.sleep(PING_INTERVAL_SECONDS)

    def __process_tasks_queue(self) -> None:
        """Keep checking queue for incoming tasks (and execute them)."""
        try:
            while True:
                self.log.info("Waiting for new tasks....")
                run_to_execute = self.runs_queue.get()
                self.log.info("New task received")
                self.__start_task(run_to_execute)

        except (KeyboardInterrupt, InterruptedError):
            self.log.info("Node is interrupted, shutting down...")
            self.cleanup()
            sys.exit()

    def kill_containers(self, kill_info: dict) -> list[dict]:
        """
        Kill containers on instruction from socket event

        Parameters
        ----------
        kill_info: dict
            Dictionary received over websocket with instructions for which
            tasks to kill

        Returns
        -------
        list[dict]:
            List of dictionaries with information on killed task (keys:
            run_id, task_id and parent_id)
        """
        if kill_info["collaboration_id"] != self.client.collaboration_id:
            self.log.debug(
                "Not killing tasks as this node is in another collaboration."
            )
            return []
        elif "node_id" in kill_info and kill_info["node_id"] != self.client.whoami.id_:
            self.log.debug(
                "Not killing tasks as instructions to kill tasks were directed"
                " at another node in this collaboration."
            )
            return []

        # kill specific task if specified, else kill all algorithms
        kill_list = kill_info.get("kill_list")
        if kill_list:
            kill_list = [ToBeKilled(**kill_info) for kill_info in kill_list]
        killed_algos = self.k8s_container_manager.kill_tasks(kill_list=kill_list)
        # update logs of killed tasks. Note that the status is already set to KILLED
        # by the server.
        for killed_algo in killed_algos:
            self.client.run.patch(
                id_=killed_algo.run_id,
                data={
                    "log": killed_algo.logs,
                },
            )
        return killed_algos

    def share_node_details(self) -> None:
        """
        Share part of the node's configuration with the server.

        This helps the other parties in a collaboration to see e.g. which
        algorithms they are allowed to run on this node.
        """
        # check if node allows to share node details, otherwise return
        if not self.config.get("share_config", True):
            self.log.debug(
                "Not sharing node configuration in accordance with "
                "the configuration setting."
            )
            return

        config_to_share = {}

        encryption_config = self.config.get("encryption")
        if encryption_config:
            if encryption_config.get("enabled") is not None:
                config_to_share[NodeConfigKey.ENCRYPTION.value] = str(
                    encryption_config.get("enabled")
                )

        # share node policies (e.g. who can run which algorithms)
        policies = self.config.get("policies", {})
        config_to_share[NodeConfigKey.ALLOWED_ALGORITHMS.value] = policies.get(
            NodePolicy.ALLOWED_ALGORITHMS.value, "all"
        )
        if policies.get(NodePolicy.ALLOWED_USERS.value) is not None:
            config_to_share[NodeConfigKey.ALLOWED_USERS.value] = policies.get(
                NodePolicy.ALLOWED_USERS.value
            )
        if policies.get(NodePolicy.ALLOWED_ORGANIZATIONS.value) is not None:
            config_to_share[NodeConfigKey.ALLOWED_ORGANIZATIONS.value] = policies.get(
                NodePolicy.ALLOWED_ORGANIZATIONS.value
            )

        # share node database labels and types to help people extract data from
        # databases in the UI

        labels = []
        types = {}
        for label, db_info in self.k8s_container_manager.databases.items():
            type_ = db_info.type
            labels.append(label)
            types[f"db_type_{label}"] = type_

        config_to_share[NodeConfigKey.DATABASE_LABELS.value] = labels
        config_to_share[NodeConfigKey.DATABASE_TYPES.value] = types

        self.log.debug("Sharing node configuration: %s", config_to_share)
        self.socketIO.emit("node_info_update", config_to_share, namespace="/tasks")

    def cleanup(self) -> None:
        try:
            if hasattr(self, "socketIO") and self.socketIO:
                self.socketIO.disconnect()
        except Exception as e:
            self.log.exception("Error while disconnecting from socketIO: %s", e)

        try:
            if hasattr(self, "k8s_container_manager"):
                self.k8s_container_manager.cleanup()
        except Exception as e:
            self.log.exception("Error while cleaning up k8s container manager: %s", e)

        self.log.info("Bye!")

    def start_processing_threads(self) -> None:
        """
        Start the threads that (1) consumes the queue with the requests produced by the server, and
        (2) polls the K8S server for finished jobs, collects their output, and send it to the server;
        """
        self.log.info("Starting threads")
        # polls for results on completed jobpods using the k8s api, also reports the results (or error status) back to the server
        results_polling_thread = threading.Thread(target=self.__poll_task_results)
        # polls for new tasks sent by the server, and starts them using the k8s API
        queue_processing_thread = threading.Thread(target=self.__process_tasks_queue)
        results_polling_thread.start()
        queue_processing_thread.start()


# ------------------------------------------------------------------------------
def run(ctx):
    """Start the node."""
    node = Node(ctx)
