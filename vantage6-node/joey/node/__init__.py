"""Node that is responsible for retreiving tasks and executing them.

It uses 4 threads: 
    * main thread, waits for new tasks to be added to the queue and 
        run the tasks
    * listening thread, listens for incommin websocket messages. Which 
        are handled by NodeTaskNamespace.
    * speaking thread, waits for results from docker to return and posts
        them at the central server
    * proxy server thread, provides an interface for master containers
        to post tasks and retrieve results

"""
import sys
import os
import time
import datetime
import logging
import queue
import typing
import shutil
import requests

from pathlib import Path
from threading import Thread
from socketIO_client import SocketIO, SocketIONamespace
from gevent.pywsgi import WSGIServer

import joey.constants as cs

from joey.node.docker_manager import DockerManager
from joey.node.server_io import ClientNodeProtocol, ServerInfo
from joey.node.proxy_server import app 
from joey.util import logger_name

class NodeTaskNamespace(SocketIONamespace):
    """Class that handles incoming websocket events."""

    # reference to the node objects, so a callback can edit the 
    # node instance.
    node_worker_ref = None

    def __init__(self, *args, **kwargs):
        """Create a new handler for a socket namespace."""
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger(logger_name(__name__))
        self.node_worker_ref = None

    def setNodeWorker(self, node_worker):
        """Sets a reference to the NodeWorker that created this Namespace."""
        self.node_worker_ref = node_worker

    def on_disconnect(self):
        """Callback when the server disconnects."""
        self.log.debug('diconnected callback')
        self.log.info('Disconnected from the server')
    
    def on_new_task(self, task_id):
        """Callback to fetch new available tasks."""
        if self.node_worker_ref:
            self.node_worker_ref.get_task_and_add_to_queue(task_id)
            self.log.info(f'New task has been added task_id={task_id}')
        else:
            msg = 'Task Master Node reference not set is socket namespace'
            self.log.critical(msg)

    def on_container_failed(self, run_id):
        self.log.critical(
            f"A container on a node within your collaboration part of run_id="
            f"{run_id} has exited with a non-zero status_code"
        )
    #     #TODO handle run sequence on this node

# ------------------------------------------------------------------------------
class NodeWorker(object):
    """Automated node that checks for tasks and executes them."""

    def __init__(self, ctx):
        """ Initialize a new TaskMasterNode instance."""
        self.log = logging.getLogger(logger_name(__name__))

        self.ctx = ctx
        self.config = ctx.config
        
        # initialize Node connection to the server
        self.server_io = ClientNodeProtocol(
            host=self.config.get('server_url'), 
            port=self.config.get('port'),
            path=self.config.get('api_path')
        )

        self.log.info(f"Connecting server: {self.server_io.base_path}")

        # Authenticate to the DL server, obtaining a JSON Web Token.
        # Note that self.authenticate() blocks until it succeeds.
        self.log.debug("authenticating")
        self.authenticate()

        # after we authenticated we setup encryption
        
        self.server_io.setup_encryption(
            self.config.get("encryption").get("private_key")
        )

        # Create a long-lasting websocket connection.
        self.log.debug("creating socket connection with the server")
        self.__connect_to_socket()

        # listen forever for incoming messages, tasks are stored in
        # the queue.
        self.queue = queue.Queue()
        self.log.debug("start thread for incoming messages (tasks)")
        t = Thread(target=self.__listening_worker, daemon=True)
        t.start()

        # check if new tasks were posted while offline.
        self.log.debug("fetching tasks that were posted while offline")
        self.__sync_task_que_with_server() 

        # TODO read allowed repositories from the config file
        self.log.debug("setup the docker manager")
        self.__docker = DockerManager(
            allowed_repositories=[], 
            docker_socket_path="unix://var/run/docker.sock",
            tasks_dir=self.ctx.data_dir,
            isolated_network_name=f"{ctx.docker_network_name}-net"
        )

        # copy data to Volume /mnt/data-volume from /mnt/data to populate
        # the volume for use in the algorithm containers (which can not access
        # the host directly)
        self.log.debug("copying data files to volume")
        shutil.copy2("/mnt/database.csv", "/mnt/data-volume", follow_symlinks=True)

        # connect itself to the isolated algorithm network
        self.log.debug("connect to isolated algorithm network")
        self.__docker.isolated_network.connect(
            ctx.docker_container_name, 
            aliases=[cs.NODE_PROXY_SERVER_HOSTNAME]
        )

        # send results to the server when they come available.
        self.log.debug("start thread for sending messages (results)")
        t = Thread(target=self.__speaking_worker, daemon=True)
        t.start()

        # proxy server for algorithm containers, so they can communicate
        # with the central server.
        self.log.info("setting up proxy server")
        t = Thread(target=self.__proxy_server_worker, daemon=True)
        t.start()

        # after here, you should/could call self.run_forever(). This 
        # could be done in a seperate Thread 
    
    def __proxy_server_worker(self):
        
        # supply the proxy server with a destination (the central server)
        # we might want to not use enviroment vars
        os.environ["SERVER_URL"] = self.server_io.host
        os.environ["SERVER_PORT"] = self.server_io.port
        os.environ["SERVER_PATH"] = self.server_io.path
        
        port = int(os.environ["PROXY_SERVER_PORT"])
        
        # app.debug = True
        app.config["SERVER_IO"] = self.server_io
        http_server = WSGIServer(
            ('0.0.0.0', port), 
            app
        )

        self.log.debug(
            f"proxyserver host={cs.NODE_PROXY_SERVER_HOSTNAME} port={port}")
        
        try:
            http_server.serve_forever()
        except Exception as e:
            self.log.critical("proxyserver crashed!...")
            self.log.debug(e)


    def authenticate(self):
        """Authenticate with the server using the api-key. If the server
        rejects for any reason we keep trying."""
        api_key = self.config.get("api_key")
        
        keep_trying = True
        while keep_trying:
            try:
                self.server_io.authenticate(api_key)

            except Exception as e:
                msg = 'Authentication failed. Retrying in 10 seconds!'
                self.log.warning(msg)
                self.log.debug(e)
                time.sleep(10)

            else:
                # This is only executed if try-block executed without error.
                keep_trying = False 

        # At this point, we shoud be connnected.
        self.log.info(f"Node name: {self.server_io.name}")

    def get_task_and_add_to_queue(self, task_id):
        """Fetches (open) task with task_id from the server. 

        The task_id is delivered by the websocket-connection.
        """
        assert self.server_io.cryptor, "Encrpytion has not been setup"

        # fetch (open) result for the node with the task_id
        tasks = self.server_io.get_results(
            include_task=True,
            state='open',
            task_id=task_id
        )

        # in the current setup, only a single result for a single node 
        # in a task exists.
        for task in tasks:
    
            try:
                task["input"] = self.server_io.cryptor.decrypt(task["input"])
            except ValueError as e:
                self.log.error(
                    "Unable to decrypt input, assuming it was unencrypted")
                self.log.debug(e)

            self.queue.put(task)

    def __sync_task_que_with_server(self):
        """Get all unprocessed tasks from the server for this node."""
        assert self.server_io.cryptor, "Encrpytion has not been setup"

        # make sure we do not add the same job twice. 
        self.queue = queue.Queue()

        # request open tasks from the server
        tasks = self.server_io.get_results(state="open", include_task=True)
        for task in tasks:
            
            try:
                task["input"] = self.server_io.cryptor.decrypt(task["input"])
            except ValueError as e:
                self.log.error(
                    "Unable to decrypt message, assuming it was unencrypted"
                )
                self.log.debug(e)

            self.queue.put(task)

        self.log.info(f"received {self.queue._qsize()} tasks" )

    def run_forever(self):
        """Connect to the server to obtain and execute tasks forever"""
        try:
            while True:
                # blocking untill a task comes available
                # timeout specified, else Keyboard interupts are ignored
                self.log.info("Waiting for new tasks....")
                while True:
                    try:
                        task = self.queue.get(timeout=1)
                        break

                    except queue.Empty:
                        pass

                # if task comes available, attempt to execute it
                try:
                    self.__start_task(task)
                except Exception as e:
                    self.log.exception(e)

        except KeyboardInterrupt:
            self.log.debug("Caught a keyboard interupt, shutting down...")
            self.socketIO.disconnect()
            sys.exit()
    
    def __start_task(self, taskresult):
        """Start the docker image and notify the server that the task 
        has been started."""

        task = taskresult['task']
        self.log.info("Starting task {id} - {name}".format(**task))

        # notify that we are processing this task
        self.server_io.set_task_start_time(taskresult["id"])

        # TODO possibly we want to limit the token handout
        token = self.server_io.request_token_for_container(
            task["id"], 
            task["image"]
        )
        token = token["container_token"]

        # If the task has the variable 'database' set and its value corresponds
        # to a database defined in the configuration, we'll use that.
        if (task['database'] 
            and self.config.get('databases') 
            and task['database'] in self.config['databases']):
            database_uri = self.config['databases'][task['database']]
        else:
            database_uri = self.config['databases']["default"]

        # create a temporary volume for each run_id (tmp_{run_id})
        self.__docker.create_temporary_volume(task["run_id"])
        # self.__docker.client.containers.get(self.ctx.docker_container_name)

        # start docker container in the background
        self.__docker.run(
            result_id=taskresult["id"], 
            image=task["image"],
            database_uri=database_uri,
            docker_input=taskresult['input'],
            run_id=task["run_id"],
            token=token
        )

    def __connect_to_socket(self):
        """Create long-lasting websocket connection with the server. 

        THe connection is used to receive status updates, such as 
        new tasks.
        """
        
        self.socketIO = SocketIO(
            self.server_io.host, 
            port=self.server_io.port, 
            headers=self.server_io.headers,
            wait_for_connection=True
        )
        
        # define() returns the instantiated action_handler 
        self.socket_tasks = self.socketIO.define(NodeTaskNamespace, '/tasks')
        self.socket_tasks.setNodeWorker(self)

        # Log the outcome
        if self.socketIO.connected:
            msg = 'connected to host={host} on port={port}'
            msg = msg.format(
                host=self.server_io.host, 
                port=self.server_io.port
            )
            self.log.info(msg)

        else:
            msg = 'could *not* connect to {host} on port={port}'
            msg = msg.format(
                host=self.server_io.host, 
                port=self.server_io.port
            )
            self.log.critical(msg)
        
    def __listening_worker(self):
        """Listen for incoming (websocket) messages from the server.

        Runs in a separate thread. Received events are dispatched
        through the appropriate action_handler for a channel.
        """
        self.log.debug("listening for incoming messages")
        while True:
            # incoming messages are handled by the action_handler instance which 
            # is attached when the socket connection was made. wait is blocking 
            # forever (if no time is specified).
            self.socketIO.wait()

    def __speaking_worker(self):
        """Routine that is in a seperate thread sending results
        to the server when they come available."""
        
        self.log.debug("Waiting for results to send to the server")

        while True:
            results = self.__docker.get_result()
            
            # notify all of a crashed container
            if results.status_code: 
                self.socket_tasks.emit(
                    'container_failed', 
                    self.server_io.id,
                    results.status_code,
                    results.result_id,
                    self.server_io.collaboration_id
                )
                
            self.log.info(
                f"Results (id={results.result_id}) are sent to the server!")

            #TODO change to a single request, might need to reconsider the flow
            response = self.server_io.request(f"result/{results.result_id}")
            task_id = response.get("task_id")
            response = self.server_io.request(f"task/{task_id}")
            initiator_id = response.get("initiator_id")

            self.server_io.patch_results(
                id=results.result_id,
                initiator_id=initiator_id,
                result={
                    'result': results.data,
                    'log': results.logs,
                    'finished_at': datetime.datetime.now().isoformat(),
                }
            )

# ------------------------------------------------------------------------------
def run(ctx):
    """Run the node."""
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # initialize node, connect to the server using websockets
    tmc = NodeWorker(ctx)

    # put the node to work, executing tasks that are in the que
    tmc.run_forever()
