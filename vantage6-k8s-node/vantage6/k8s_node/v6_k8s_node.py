from vantage6.common.client.node_client import NodeClient
from threading import Thread
from vantage6.node import proxy_server
from vantage6.common.log import get_file_logger
from gevent.pywsgi import WSGIServer
from vantage6.common.exceptions import AuthenticationException
from vantage6.common import logger_name
from vantage6.node.socket import NodeTaskNamespace
from vantage6.cli.context.node import NodeContext
from vantage6.common.enum import RunStatus
from vantage6.node.util import get_parent_id
from vantage6.k8s_node.log_manager import logs_setup
from vantage6.k8s_node.csv_utils import get_csv_column_names

from vantage6.node.globals import (
    NODE_PROXY_SERVER_HOSTNAME,
    SLEEP_BTWN_NODE_LOGIN_TRIES,
    TIME_LIMIT_RETRY_CONNECT_NODE,
    TIME_LIMIT_INITIAL_CONNECTION_WEBSOCKET,
)

from vantage6.k8s_node.container_manager import ContainerManager
from vantage6.k8s_node import pod_node_constants

from socketio import Client as SocketIO
import logging
from logging import handlers
import traceback
import random
import requests
import time
import os
import queue
import json
import pprint
import datetime
import sys
import threading


# Based on https://github.com/vantage6/vantage6/blob/be2e82b33e68db74304ea01c778094e6b40e671a/vantage6-node/vantage6/node/__init__.py#L1

class NodePod:

    def __init__(self, ctx: NodeContext):
        self.log = logging.getLogger(logger_name(__name__))
        self.ctx = ctx

        # Added for the PoC
        self.k8s_container_manager = ContainerManager(ctx)

        # Initialize the node. If it crashes, shut down the parts that started
        # already
        try:
            self.initialize()
        except Exception:
            self.cleanup()
            raise    

    
    def initialize(self) -> None:

        self.config = self.ctx.config
        self.debug: dict = self.config.get("debug", {})
        self._using_encryption = None
        
        self.client = NodeClient(
                    host=self.config.get("server_url"),
                    port=self.config.get("port"),
                    path=self.config.get("api_path"),
                )
        self.log.info(f"Connecting server: {self.client.base_path}")
        self.queue = queue.Queue()
        self.log.debug("Authenticating")
        self.authenticate()

        #TODO check/setup collaboration encryption status
        self.setup_encryption()

        # Thread for proxy server for algorithm containers, so they can
        # communicate with the central server.
        t = Thread(target=self.__proxy_server_worker, daemon=True)
        t.start()

        # Create a long-lasting websocket connection.
        self.log.debug("Creating websocket connection with the server")
        self.connect_to_socket()

    def __proxy_server_worker(self) -> None:
        """
        Proxy algorithm container communcation.

        A proxy for communication between algorithms and central
        server.
        """
        if self.k8s_container_manager.running_on_guest_env:
            default_proxy_host = pod_node_constants.V6_NODE_FQDN
        else:            
            #TODO to be removed
            default_proxy_host = "host.docker.internal"
            
        # If PROXY_SERVER_HOST was set in the environment, it overrides our
        # value.
        proxy_host = os.environ.get("PROXY_SERVER_HOST", default_proxy_host)
        os.environ["PROXY_SERVER_HOST"] = proxy_host

        #proxy_port = int(os.environ.get("PROXY_SERVER_PORT", 8080))
        proxy_port = pod_node_constants.V6_NODE_PROXY_PORT

        # 'app' is defined in vantage6.node.proxy_server
        debug_mode = self.debug.get("proxy_server", False)
        if debug_mode:
            self.log.debug("Debug mode enabled for proxy server")
            proxy_server.app.debug = True
        proxy_server.app.config["SERVER_IO"] = self.client
        
        #The value on the module variable 'server_url' defines the target of the 'make_request' method.
        #TODO improve encapsulation here - why proxy_server.server_url, and proxy_host?
        proxy_server.server_url = self.client.base_path
        self.log.info(">>>> Setting target endpoint for the algorithm's client as : %s",proxy_server.server_url)            

        self.log.info("Starting proxyserver at '%s:%s'", proxy_host, proxy_port)            


        # set up proxy server logging
        log_level = getattr(logging, self.config["logging"]["level"].upper())
        self.proxy_log = get_file_logger(
            "proxy_server", self.ctx.proxy_log_file, log_level_file=log_level
        )

        # this is where we try to find a port for the proxyserver
        for try_number in range(5):
            self.log.info("Starting proxyserver at '%s:%s'", proxy_host, proxy_port)            
            http_server = WSGIServer(
                ("0.0.0.0", proxy_port), proxy_server.app, log=self.proxy_log
            )

            try:
                http_server.serve_forever()
                

            except OSError as e:
                self.log.info("Error during attempt %s", try_number)
                self.log.info("%s: %s", type(e), e)

                if e.errno == 48:
                    proxy_port = random.randint(2048, 16384)
                    self.log.warning("Retrying with a different port: %s", proxy_port)
                    os.environ["PROXY_SERVER_PORT"] = str(proxy_port)

                else:
                    raise

            except Exception as e:
                self.log.error("Proxyserver could not be started or crashed!")
                self.log.error(e)

            


    def sync_task_queue_with_server(self) -> None:
        """Get all unprocessed tasks from the server for this node.
            Method Linked to a Socket.io event : on_sync)    
            This method:
                - Check for encryption settings
                - Get 'open' tasks   (@Question What does 'open' mean in this context?)
                - Add these task to the queue        
        """
        assert self.client.cryptor, "Encrpytion has not been setup"

        # request open tasks from the server
        task_results = self.client.run.list(state="open", include_task=True)
        self.log.debug("task_results: %s", task_results)

        # add the tasks to the queue
        self.__add_tasks_to_queue(task_results)
        self.log.info("Received %s tasks", self.queue._qsize())



    def get_task_and_add_to_queue(self, task_id: int) -> None:            
            """
            Fetches (open) task with task_id from the server. The `task_id` is
            delivered by the websocket-connection.

            Linked to Socket.io event - on_new_task

            Parameters
            ----------
            task_id : int
                Task identifier
            """
            # fetch open algorithm runs for this node
            task_runs = self.client.run.list(
                include_task=True, state="open", task_id=task_id
            )

            # add the tasks to the queue
            self.__add_tasks_to_queue(task_runs)



    def __add_tasks_to_queue(self, task_results: list[dict]) -> None:
        """
        Add a task to the queue.

        #POC task_result: misleading variable name?

        Parameters
        ----------
        taskresult : list[dict]
            A list of dictionaries with information required to run the
            algorithm
        """
        for task_result in task_results:

            try:
                print(f"K8S >>>>> Is task {task_result['id']} running?:{self.k8s_container_manager.is_running(task_result['id'])}")             
                
                if not self.k8s_container_manager.is_running(task_result['id']):
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
        self.client.set_task_start_time(task_incl_run["id"])

        token = self.client.request_token_for_container(task["id"], task["image"])
        token = token["container_token"]

        # create a temporary volume for each job_id
        #vol_name = self.ctx.docker_temporary_volume_name(task["job_id"])
        #self.__docker.create_volume(vol_name)

        # (message from the original source code) 
        # For some reason, if the key 'input' consists of JSON, it is
        # automatically marshalled? This causes trouble, so we'll serialize it
        # again.
        # FIXME: should probably find & fix the root cause?
        if type(task_incl_run["input"]) == dict:
            task_incl_run["input"] = json.dumps(task_incl_run["input"])

        # Run the container. This adds the created container/task to the list
        # __docker.active_tasks
        # PoC running with K8S Container Manager
        
        task_status, vpn_ports = self.k8s_container_manager.run(
            run_id=task_incl_run["id"],
            task_info=task,
            image=task["image"],
            docker_input=task_incl_run["input"],
            tmp_vol_name="****tmp_vol_name key is deprecated",
            token=token,
            databases_to_use=task.get("databases", []),
        )

        # save task status to the server
        update = {"status": task_status}
        if task_status == RunStatus.NOT_ALLOWED:
            # set finished_at to now, so that the task is not picked up again
            # (as the task is not started at all, unlike other crashes, it will
            # never finish and hence not be set to finished)
            update["finished_at"] = datetime.datetime.now().isoformat()
        self.client.run.patch(id_=task_incl_run["id"], data=update)

        # ensure that the /tasks namespace is connected. This may take a while
        # (usually < 5s) when the socket just (re)connected
        MAX_ATTEMPTS = 30
        retries = 0
        while "/tasks" not in self.socketIO.namespaces and retries < MAX_ATTEMPTS:
            retries += 1
            self.log.debug("Waiting for /tasks namespace to connect...")
            time.sleep(1)
        self.log.debug("Connected to /tasks namespace")
        # in case the namespace is still not connected, the socket notification
        # will not be sent to other nodes, but the task will still be processed

        # send socket event to alert everyone of task status change
        self.socketIO.emit(
            "algorithm_status_change",
            data={
                "node_id": self.client.whoami.id_,
                "status": task_status,
                "run_id": task_incl_run["id"],
                "task_id": task["id"],
                "collaboration_id": self.client.collaboration_id,
                "organization_id": self.client.whoami.organization_id,
                "parent_id": get_parent_id(task),
            },
            namespace="/tasks",
        )

    def __poll_task_results(self):
        """
        Polls the K8S server for finished jobs
        """
        
        #Prevent the K8S rest client from creating DEBUG logging messages (these may lead to unnecesarily
        # massive log files)

        self.log.info("Starting node's task results polling thread")
        try:        
            while True:    
                time.sleep(1)
                next_result = self.k8s_container_manager.get_result()
                self.log.info(f"""
                    *********************************************************************************  
                    EVENT @ NODE - task result reported. The following will be notified to the server:
                    {next_result}
                    *********************************************************************************  
                    """)
                
                                #Notify other nodes about algorithm status change
                self.log.info(f"Sending result (run={next_result.run_id}) to the server!")

                response = self.client.request(f"task/{next_result.task_id}")

                init_org = response.get("init_org")            

                self.client.run.patch(
                    id_=next_result.run_id,
                    data={
                        "result": next_result.data,
                        "log":next_result.logs[0],
                        "status": next_result.status,
                        "finished_at": datetime.datetime.now().isoformat(),
                    },
                    init_org_id=init_org.get("id"),
                )
                
                # notify other nodes about algorithm status change
                self.socketIO.emit(
                    "algorithm_status_change",
                    data={
                        "node_id": self.client.whoami.id_,
                        "status": next_result.status,
                        "run_id": next_result.run_id,
                        "task_id": next_result.task_id,
                        "collaboration_id": self.client.collaboration_id,
                        "organization_id": self.client.whoami.organization_id,
                        "parent_id": next_result.parent_id,
                    },
                    namespace="/tasks",
                )





                
        except (KeyboardInterrupt, InterruptedError):
            self.log.info("Node is interrupted, shutting down...")
            self.cleanup()
            sys.exit()






    def __print_connection_error_logs(self):
        """Print error message when node cannot find the server"""
        self.log.warning("Could not connect to the server. Retrying in 10 seconds")




    def authenticate(self):
        """
        Authenticate with the server using the api-key from the configuration
        file. If the server rejects for any reason -other than a wrong API key-
        serveral attempts are taken to retry.
        """

        TIME_LIMIT_RETRY_CONNECT_NODE = 60
        SLEEP_BTWN_NODE_LOGIN_TRIES = 2

        api_key = self.ctx.config.get("api_key")

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

    def setup_encryption(self) -> None:
        #TODO check collaboration encryption configuration    
        """Setup encryption if the node is part of encrypted collaboration"""
        encrypted_collaboration = self.client.is_encrypted_collaboration()
        encrypted_node = self.config["encryption"]["enabled"]

        if encrypted_collaboration != encrypted_node:
            # You can't force it if it just ain't right, you know?
            raise Exception("Expectations on encryption don't match?!")

        if encrypted_collaboration:
            self.log.warning("Enabling encryption!")
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
        #debug_mode = self.debug.get("socketio", False)
        #if debug_mode:
        #    self.log.debug("Debug mode enabled for socketio")
        
        self.socketIO = SocketIO(
            request_timeout=60 #, logger=debug_mode, engineio_logger=debug_mode
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
            
            PING_INTERVAL_SECONDS = 60
            
            # Wait before sending next ping
            time.sleep(PING_INTERVAL_SECONDS)

    def __process_tasks_queue(self) -> None:
        # previously called def run_forever(self) -> None:

        """
        Keep checking queue for incoming tasks (and execute them).

            Note: In the original version SIGINT/SIGTERM signals were also captured to guarantee a gracefuly shutdown of the containers.
            E.g., aborting the node with CTRL-C would lead to a container execution inconsistent state, as these are handled by the node.
            
            In this new version the K8S server would keep running idependently of the node status. How to ensure consistency after an
            abrupt failure should be further explored.


            taskresult: misleading name? not the result of a task, but a task description

        """
         
        try:
            while True:
                self.log.info("********************  Waiting for new tasks....")
                taskresult = self.queue.get()
                self.log.info(">>>>> New task received")
                pprint.pp(taskresult)
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

        killed_algos = self.__docker.kill_tasks(
            org_id=self.client.whoami.organization_id, kill_list=kill_list
        )
        # update status of killed tasks
        for killed_algo in killed_algos:
            self.client.run.patch(
                id_=killed_algo.run_id, data={"status": RunStatus.KILLED}
            )
        return killed_algos
        """
        #PoC TODO, using k8s container manager
        print(f">>>>>>>Here I'm supposed to kill a runnin job pod given this info: {json.dumps(kill_info, indent = 4)}")
        return []
        
        """"
        kill_info:
            "kill_list": [
                {
                    "task_id": 3,
                    "run_id": 3,
                    "organization_id": 2
                }
            ],
            "collaboration_id": 1
    
        """




    
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
                config_to_share["encryption"] = encryption_config.get("enabled")

        # share node policies (e.g. who can run which algorithms)
        policies = self.config.get("policies", {})
        config_to_share["allowed_algorithms"] = policies.get(
            "allowed_algorithms", "all"
        )
        if policies.get("allowed_users") is not None:
            config_to_share["allowed_users"] = policies.get("allowed_users")
        if policies.get("allowed_organizations") is not None:
            config_to_share["allowed_orgs"] = policies.get("allowed_organizations")

        # share node database labels, types, and column names (if they are
        # fixed as e.g. for csv file)
        labels = []
        types = {}
        col_names = {}
        for db in self.config.get("databases", []):
            label = db.get("label")
            type_ = db.get("type")
            labels.append(label)
            types[f"db_type_{label}"] = type_

            if type_ in ("csv"):
                csv_path = db.get("uri")
                #If the node is running within a host, use the uri, as 
                #defined in the config file.
                #if the node is running within a POD, by convention 
                # (see kubeconfs/node_pod_config.yaml), the uri is the
                # same with the prefix defined in node_constants.V6_NODE_DATABASE_BASE_PATH
                if self.k8s_container_manager.running_on_guest_env:                    
                    col_names[f"columns_{label}"] = get_csv_column_names(os.path.join(pod_node_constants.V6_NODE_DATABASE_BASE_PATH, csv_path.lstrip('/')))
                else:
                    col_names[f"columns_{label}"] = get_csv_column_names(csv_path)
        config_to_share["database_labels"] = labels
        config_to_share["database_types"] = types
        if col_names:
            config_to_share["database_columns"] = col_names

        self.log.debug("Sharing node configuration: %s", config_to_share)
        self.socketIO.emit("node_info_update", config_to_share, namespace="/tasks")        

    def cleanup(self) -> None:
        # TODO add try/catch for all cleanups so that if one fails, the others are
        # still executed

        if hasattr(self, "socketIO") and self.socketIO:
            self.socketIO.disconnect()
        """
        TODO include these if apply to the POC:        
        if hasattr(self, "vpn_manager") and self.vpn_manager:
            self.vpn_manager.exit_vpn()
        if hasattr(self, "ssh_tunnels") and self.ssh_tunnels:
            for tunnel in self.ssh_tunnels:
                tunnel.stop()
        if hasattr(self, "_Node__docker") and self.__docker:
            self.__docker.cleanup()
        """

        self.log.info("Bye!")








    """"
        task_results sample:
        
        {
        'status': 'pending',
        'node': {'id': 2,
                'status': 'online',
                'name': 'collab-of-k8s-enabled-orgs - kube-org-a',
                'ip': None},
        'results': {'id': 9, 'link': '/api/result/9', 'methods': ['GET', 'PATCH']},
        'id': 9,
        'task': {'status': 'pending',
                'study': None,
                'name': 'asd',
                'results': '/api/result?task_id=9',
                'init_user': {'id': 4,
                                'link': '/api/user/4',
                                'methods': ['DELETE', 'PATCH', 'GET']},
                'description': '',
                'children': '/api/task?parent_id=9',
                'job_id': 9,
                'databases': [{'label': 'default', 'parameters': '{}'}],
                'id': 9,
                'created_at': '2024-07-22T20:51:53.787815',
                'init_org': {'id': 2,
                            'link': '/api/organization/2',
                            'methods': ['GET', 'PATCH']},
                'image': 'harbor2.vantage6.ai/demo/average',
                'parent': None,
                'collaboration': {'id': 1,
                                    'link': '/api/collaboration/1',
                                    'methods': ['DELETE', 'PATCH', 'GET']}},
        'assigned_at': '2024-07-22T20:51:53.874029',
        'log': None,
        'finished_at': None,
        'input': b'{"method":"partial_average","kwargs":{"column_name":"col_a"}}',
        'started_at': None,
        'organization': {'id': 2,
                        'link': '/api/organization/2',
                        'methods': ['GET', 'PATCH']},
    """


    def start_processing_threads(self) -> None:
        """
        Start the threads that (1) consumes the queue with the requests produced by the server, and 
        (2) polls the K8S server for finished jobs, collects their output, and send it to the server;  
        """
        self.log.info("Starting threads")
        #polls for results on completed jobpods using the k8s api, also reports the results (or error status) back to the server
        results_polling_thread = threading.Thread(target=self.__poll_task_results)
        #polls for new tasks sent by the server, and starts them using the k8s API
        queue_processing_thread = threading.Thread(target=self.__process_tasks_queue)
        results_polling_thread.start()
        queue_processing_thread.start()
        
    





if __name__ == '__main__':
    logs_setup()

    # Config file path - exists when the node is running within a POD (see kubeconfs/node_pod_config.yaml)
    containeridzed_node_config_absolute_path = "/app/.v6node/configs/node_legacy_config.yaml"
    # Regular (non-containerized node) configuration file path
    node_config_relative_path = "configs/node_legacy_config.yaml"

    if os.path.exists(containeridzed_node_config_absolute_path):
        print("Starting the node from within a Kubernetes POD")
        ctx=NodeContext(instance_name='poc_instance', system_folders=False, config_file=containeridzed_node_config_absolute_path)
    else:
        print("Attempting to start the node from a regular host")
        node_config_absolute_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), node_config_relative_path)
        ctx=NodeContext(instance_name='poc_instance', system_folders=False, config_file=node_config_absolute_path)
    
    node = NodePod(ctx)
    node.start_processing_threads()
    
    


