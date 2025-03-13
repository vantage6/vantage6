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
import json
import logging
import os
import queue
import random
import sys
import time
import threading
from pathlib import Path
from threading import Thread

import requests.exceptions
from gevent.pywsgi import WSGIServer
from socketio import Client as SocketIO

from vantage6.cli.context.node import NodeContext
from vantage6.common import logger_name
from vantage6.common.client.node_client import NodeClient
from vantage6.common.enum import AlgorithmStepType, RunStatus, TaskStatusQueryOptions
from vantage6.common.exceptions import AuthenticationException
from vantage6.common.globals import PING_INTERVAL_SECONDS, NodePolicy
from vantage6.common.log import get_file_logger

# make sure the version is available
from vantage6.node._version import __version__  # noqa: F401
from vantage6.node.globals import (
    SLEEP_BTWN_NODE_LOGIN_TRIES,
    TIME_LIMIT_INITIAL_CONNECTION_WEBSOCKET,
    TIME_LIMIT_RETRY_CONNECT_NODE,
    PROXY_SERVER_HOST,
    PROXY_SERVER_PORT,
)
from vantage6.node.k8s.container_manager import ContainerManager
from vantage6.node.socket import NodeTaskNamespace
from vantage6.node.util import get_parent_id
from vantage6.node import proxy_server


# ------------------------------------------------------------------------------
class Node:
    """
    Authenticates to the central server, setup encryption, a
    websocket connection, retrieving task that were posted while
    offline, preparing dataset for usage and finally setup a
    local proxy server..

    Parameters
    ----------
    ctx: NodeContext | DockerNodeContext
        Application context object.

    """

    def __init__(self, ctx: NodeContext):
        self.log = logging.getLogger(logger_name(__name__))
        self.ctx = ctx

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
        self.client = NodeClient(
            host=self.config.get("server_url"),
            port=self.config.get("port"),
            path=self.config.get("api_path"),
        )

        self.k8s_container_manager = ContainerManager(self.ctx, self.client)

        # ensure that the namespace to create tasks in is set up correctly or try to
        # create it
        self.log.debug("Ensuring that the task namespace is properly configured")
        namespace_created = self.k8s_container_manager.ensure_task_namespace()
        if not namespace_created:
            self.log.error("Could not create the task namespace. Exiting.")
            exit(1)

        self.log.info(f"Connecting server: {self.client.base_path}")

        # Authenticate with the server, obtaining a JSON Web Token.
        # Note that self.authenticate() blocks until it succeeds.
        self.queue = queue.Queue()
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

        self.log.info("Init complete")

    def __proxy_server_worker(self) -> None:
        """
        Proxy algorithm container communcation.

        A proxy for communication between algorithms and central
        server.
        """
        default_proxy_host = PROXY_SERVER_HOST

        # If PROXY_SERVER_HOST was set in the environment, it overrides our
        # value.
        proxy_host = os.environ.get("PROXY_SERVER_HOST", default_proxy_host)
        os.environ["PROXY_SERVER_HOST"] = proxy_host

        proxy_port = int(os.environ.get("PROXY_SERVER_PORT", PROXY_SERVER_PORT))

        # 'app' is defined in vantage6.node.proxy_server
        debug_mode = self.debug.get("proxy_server", False)
        if debug_mode:
            self.log.debug("Debug mode enabled for proxy server")
            proxy_server.app.debug = True
        proxy_server.app.config["SERVER_IO"] = self.client

        # The value on the module variable 'server_url' defines the target of the 'make_request' method.
        # TODO improve encapsulation here - why proxy_server.server_url, and proxy_host?
        proxy_server.server_url = self.client.base_path
        self.log.info(
            "Setting target endpoint for the algorithm's client as : %s",
            proxy_server.server_url,
        )

        self.log.info("Starting proxyserver at '%s:%s'", proxy_host, proxy_port)

        # set up proxy server logging
        Path(self.ctx.proxy_log_file).parent.mkdir(parents=True, exist_ok=True)
        log_level = getattr(logging, self.config["logging"]["level"].upper())
        self.proxy_log = get_file_logger(
            "proxy_server", self.ctx.proxy_log_file, log_level_file=log_level
        )

        # this is where we try to find a port for the proxyserver

        port_assigned = False

        for try_number in range(5):
            self.log.info("Starting proxyserver at '%s:%s'", proxy_host, proxy_port)
            http_server = WSGIServer(
                ("0.0.0.0", proxy_port), proxy_server.app, log=self.proxy_log
            )

            try:
                http_server.serve_forever()
                port_assigned = True

            except OSError as e:
                self.log.info("Error during attempt %s", try_number)
                self.log.info("%s: %s", type(e), e)

                proxy_port = random.randint(2048, 16384)
                self.log.warning("Retrying with a different port: %s", proxy_port)
                os.environ["PROXY_SERVER_PORT"] = str(proxy_port)

            except Exception as e:
                self.log.error(
                    "Proxyserver could not be started due to an unexpected error!"
                )
                self.log.exception(e)
                # After a non-os related exception there shouldn't be more retries
                exit(1)

        if not port_assigned:
            self.log.error(
                f"Unable to assing a port for the node proxy after {try_number} attempts"
            )
            exit(1)

    def sync_task_queue_with_server(self) -> None:
        """Get all unprocessed tasks from the server for this node."""
        assert self.client.cryptor, "Encrpytion has not been setup"

        # request open tasks from the server
        task_results = self.client.run.list(
            state=TaskStatusQueryOptions.OPEN.value, include_task=True
        )

        # add the tasks to the queue
        self.__add_tasks_to_queue(task_results)
        self.log.info("Received %s tasks", self.queue._qsize())

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
        task_runs = self.client.run.list(
            include_task=True, state=TaskStatusQueryOptions.OPEN.value, task_id=task_id
        )

        # add the tasks to the queue
        self.__add_tasks_to_queue(task_runs)

    def __add_tasks_to_queue(self, task_results: list[dict]) -> None:
        """
        Add a task to the queue.

        Parameters
        ----------
        taskresult : list[dict]
            A list of dictionaries with information required to run the
            algorithm
        """
        for task_result in task_results:
            try:
                if not self.k8s_container_manager.is_running(task_result["id"]):
                    self.queue.put(task_result)
                else:
                    self.log.info(
                        f"Not starting task {task_result['task']['id']} - "
                        f"{task_result['task']['name']} as it is already "
                        "running"
                    )
            except Exception:
                self.log.exception("Error while syncing task queue")

    def __start_task(self, task_incl_run: dict) -> None:
        """
        Start the docker image and notify the server that the task has been
        started.

        Parameters
        ----------
        task_incl_run : dict
            A dictionary with information required to run the algorithm
        """
        task = task_incl_run["task"]
        self.log.info("Starting task {id} - {name}".format(**task))

        # notify that we are processing this task
        task_id = task_incl_run["id"]
        self.client.set_task_start_time(task_id)

        # each algorithm container has its own purpose annotated by the action
        try:
            container_action = AlgorithmStepType(task_incl_run["action"])
        except ValueError:
            self.log.error(
                f"Unrecognized action {task_incl_run['action']}. Cancelling task."
            )
            self.client.run.patch(
                id_=task_id,
                data={
                    "status": RunStatus.FAILED,
                    "finished_at": datetime.datetime.now().isoformat(),
                    "log": f"Unrecognized action {task_incl_run['action']}",
                },
            )
            self.__emit_algorithm_status_change(task, task_incl_run, RunStatus.FAILED)
            return

        # Only compute containers need a token as they are the only ones that should
        # create subtasks
        token = ""
        if container_action == AlgorithmStepType.COMPUTE:
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
                    id_=task_incl_run["id"],
                    data={
                        "status": RunStatus.FAILED,
                        "log": "Could not obtain algorithm container token",
                    },
                )

        # For some reason, if the key 'input' consists of JSON, it is
        # automatically marshalled? This causes trouble, so we'll serialize it
        # again.
        # FIXME: should probably find & fix the root cause?
        if type(task_incl_run["input"]) == dict:
            task_incl_run["input"] = json.dumps(task_incl_run["input"])

        # Run the container. This adds the created container/task to the list
        # __docker.active_tasks
        task_status = self.k8s_container_manager.run(
            action=container_action,
            run_id=task_id,
            task_info=task,
            image=task["image"],
            docker_input=task_incl_run["input"],
            session_id=task["session"]["id"],
            token=token,
            databases_to_use=task.get("databases", []),
        )

        # save task status to the server
        update = {"status": task_status}
        if task_status == RunStatus.NOT_ALLOWED:
            # set finished_at to now, so that the task is not picked up again
            # (as the task is not started at all, unlike other crashes, it will
            # never finish and hence not be set to finished)
            update["finished_at"] = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
        self.client.run.patch(id_=task_id, data=update)

        # send socket event to alert everyone of task status change. In case the
        # namespace is not connected, the socket notification will not be sent to other
        # nodes, but the task will still be processed
        self.__emit_algorithm_status_change(task, task_incl_run, task_status)

    def __emit_algorithm_status_change(
        self, task: dict, run: dict, status: RunStatus
    ) -> None:
        """
        Emit a socket event to alert everyone of task status change.

        Parameters
        ----------
        task_id : dict
            Task metadata
        status : RunStatus
            Task status
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
                "status": status,
                "run_id": run["id"],
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
                        "status": results.status,
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
                        "status": results.status,
                        "run_id": results.run_id,
                        "task_id": results.task_id,
                        "collaboration_id": self.client.collaboration_id,
                        "organization_id": self.client.whoami.organization_id,
                        "parent_id": results.parent_id,
                    },
                    namespace="/tasks",
                )
            except Exception:
                self.log.exception("Speaking thread had an exception")

            time.sleep(1)

    def __print_connection_error_logs(self):
        """Print error message when node cannot find the server"""
        self.log.warning("Could not connect to the server. Retrying in 10 seconds")
        self.log.info(
            "Are you sure the server can be reached at %s?", self.client.base_path
        )

    def authenticate(self) -> None:
        """
        Authenticate with the server using the api-key from the configuration
        file. If the server rejects for any reason -other than a wrong API key-
        serveral attempts are taken to retry.
        """

        api_key = self.config.get("api_key")

        success = False
        i = 0
        while i < TIME_LIMIT_RETRY_CONNECT_NODE / SLEEP_BTWN_NODE_LOGIN_TRIES:
            i = i + 1
            try:
                self.client.authenticate(api_key)

            except AuthenticationException as e:
                msg = "Authentication failed: API key is wrong!"
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
            self.log.info(f"Node name: {self.client.name}")
        else:
            self.log.critical("Unable to authenticate. Exiting")
            exit(1)

        # start thread to keep the connection alive by refreshing the token
        self.client.auto_refresh_token()

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
            url=f"{self.client.host}:{self.client.port}",
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

        self.log.info(
            f"Connected to host={self.client.host} on port=" f"{self.client.port}"
        )

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
        # TODO check if this listener is used anywhere else, before removing it

        # kill_listener = ContainerKillListener()
        try:
            while True:
                self.log.info("Waiting for new tasks....")
                taskresult = self.queue.get()
                self.log.info("New task received")
                self.__start_task(taskresult)

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
        # if kill_info["collaboration_id"] != self.client.collaboration_id:
        #     self.log.debug(
        #         "Not killing tasks as this node is in another collaboration."
        #     )
        #     return []
        # elif "node_id" in kill_info and kill_info["node_id"] != self.client.whoami.id_:
        #     self.log.debug(
        #         "Not killing tasks as instructions to kill tasks were directed"
        #         " at another node in this collaboration."
        #     )
        #     return []

        # # kill specific task if specified, else kill all algorithms
        # kill_list = kill_info.get("kill_list")
        # killed_algos = self.__docker.kill_tasks(
        #     org_id=self.client.whoami.organization_id, kill_list=kill_list
        # )
        # # update status of killed tasks
        # for killed_algo in killed_algos:
        #     self.client.run.patch(
        #         id_=killed_algo.run_id, data={"status": RunStatus.KILLED}
        #     )
        # return killed_algos
        # TODO (HC) Implement using k8s container manager
        print(
            f">>>>>>>Here I'm supposed to kill a runnin job pod given this info: {json.dumps(kill_info, indent = 4)}"
        )
        return []

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
                config_to_share["encryption"] = str(encryption_config.get("enabled"))

        # share node policies (e.g. who can run which algorithms)
        policies = self.config.get("policies", {})
        config_to_share["allowed_algorithms"] = policies.get(
            NodePolicy.ALLOWED_ALGORITHMS, "all"
        )
        if policies.get(NodePolicy.ALLOWED_USERS) is not None:
            config_to_share["allowed_users"] = policies.get(NodePolicy.ALLOWED_USERS)
        if policies.get(NodePolicy.ALLOWED_ORGANIZATIONS) is not None:
            config_to_share["allowed_orgs"] = policies.get(
                NodePolicy.ALLOWED_ORGANIZATIONS
            )

        # share node database labels and types to help people extract data from
        # databases in the UI
        labels = []
        types = {}
        for db in self.config.get("databases", []):
            label = db.get("label")
            type_ = db.get("type")
            labels.append(label)
            types[f"db_type_{label}"] = type_

        config_to_share["database_labels"] = labels
        config_to_share["database_types"] = types

        self.log.debug("Sharing node configuration: %s", config_to_share)
        self.socketIO.emit("node_info_update", config_to_share, namespace="/tasks")

    def cleanup(self) -> None:
        # TODO add try/catch for all cleanups so that if one fails, the others are
        # still executed
        if hasattr(self, "socketIO") and self.socketIO:
            self.socketIO.disconnect()

        # TODO To be re-enabled once the cleanup method is implemented for the k8s container maanger
        # if hasattr(self, "_Node__docker") and self.__docker:
        #    self.__docker.cleanup()

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
