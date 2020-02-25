""" Node 

A node in its simplest would retrieve a task from the central server by 
an API call, run this task and finally return the results to the central
server again.

The node application is seperated in 4 threads: 
- main thread, waits for new tasks to be added to the queue and 
    run the tasks
- listening thread, listens for incommin websocket messages. Which 
    are handled by NodeTaskNamespace.
- speaking thread, waits for results from docker to return and posts
    them at the central server
- proxy server thread, provides an interface for master containers
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
import json

from pathlib import Path
from threading import Thread
from socketIO_client import SocketIO, SocketIONamespace
from gevent.pywsgi import WSGIServer

import vantage.constants as cs

from vantage.node.docker_manager import DockerManager
from vantage.node.server_io import ClientNodeProtocol, ServerInfo
from vantage.node.proxy_server import app 
from vantage.util import logger_name

class NodeTaskNamespace(SocketIONamespace):
    """ Class that handles incoming websocket events.
    """

    # reference to the node objects, so a callback can edit the 
    # node instance.
    node_worker_ref = None

    def __init__(self, *args, **kwargs):
        """ Handler for a websocket namespace.
        """
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger(logger_name(__name__))
        self.node_worker_ref = None

    def set_node_worker(self, node_worker):
        """ Reference NodeWorker that created this Namespace.

            This way we can call methods from the nodeworking, allowing
            for actions to be taken.

            :param node_worker: NodeWorker object 
        """
        self.node_worker_ref = node_worker

    def on_disconnect(self):
        """ Server disconnects event.
        """
        self.log.info('Disconnected from the server')
    
    def on_new_task(self, task_id):
        """ New task event.
        """
        if self.node_worker_ref:
            self.node_worker_ref.get_task_and_add_to_queue(task_id)
            self.log.info(f'New task has been added task_id={task_id}')
        else:
            self.log.critical(
                'Task Master Node reference not set is socket namespace'
            )

    def on_container_failed(self, run_id):
        """ A container in the collaboration has failed event.

            TODO handle run sequence at this node. Maybe terminate all
                containers with the same run_id?
        """
        self.log.critical(
            f"A container on a node within your collaboration part of "
            f"run_id={run_id} has exited with a non-zero status_code"
        )

    def on_expired_token(self, msg):
        self.log.warning("Your token is no longer valid... reconnect")
        self.node_worker_ref.socketIO.disconnect()
        self.log.debug("Old socket connection terminated")
        self.node_worker_ref.server_io.refresh_token()
        self.log.debug("Token refreshed")
        self.node_worker_ref.connect_to_socket()
        self.log.debug("Connected to socket")
        self.node_worker_ref.__sync_task_que_with_server()
        self.log.debug("Tasks synced again with the server...")

    def on_pang(self, msg):
        self.log.debug(f"Pong received, WS still connected <{msg}>")
        self.node_worker_ref.socket_connected = True

# ------------------------------------------------------------------------------
class NodeWorker:
    """ Node to handle incomming computation requests.

        The main steps this application follows: 1) retrieve (new) tasks
        from the central server, 2) kick-off docker algorithm containers
        based on this task and 3) retrieve the docker results and post
        them to the central server.

        TODO read allowed repositories from the config file
    """

    def __init__(self, ctx):
        """ Initialize a new NodeWorker instance.

            Authenticates to the central server, setup encrpytion, a
            websocket connection, retrieving task that were posted while
            offline, preparing dataset for usage and finally setup a 
            local proxy server.

            :param ctx: application context, see utils
        """
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
        file_ = self.config.get("encryption").get("private_key")
        if file_:
            rsa_file = Path(file_)
            if not rsa_file.exists():
                rsa_file = Path("/mnt/data/private_key.pem")
        else: 
            rsa_file = Path("/mnt/data/private_key.pem")
        
        self.server_io.setup_encryption(
            rsa_file, 
            self.config.get("encryption").get("disabled")  
        )

        # Create a long-lasting websocket connection.
        self.log.debug("creating socket connection with the server")
        self.connect_to_socket()

        # listen forever for incoming messages, tasks are stored in
        # the queue.
        self.queue = queue.Queue()
        self.log.debug("start thread for incoming messages (tasks)")
        t = Thread(target=self.__listening_worker, daemon=True)
        t.start()

        # check if new tasks were posted while offline.
        self.log.debug("fetching tasks that were posted while offline")
        self.__sync_task_que_with_server() 

        
        self.log.debug("setup the docker manager")
        self.__docker = DockerManager(
            allowed_images=self.config.get("allowed_images"), 
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

        self.log.info("starting thread to check the socker connection")
        t = Thread(target=self.__keep_socket_alive, daemon=True)
        t.start()
        # after here, you should/could call self.run_forever(). This 
        # could be done in a seperate Thread 
    
    def __proxy_server_worker(self):
        """ Proxy algorithm container communcation.

            A proxy for communication between algorithms and central 
            server.
        """
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
        """ Authenticate to the central server
        
            Authenticate with the server using the api-key. If the 
            server rejects for any reason we keep trying.
        """
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
        """ Fetches (open) task with task_id from the server. 

            The `task_id` is delivered by the websocket-connection.
        """
        
        # fetch (open) result for the node with the task_id
        tasks = self.server_io.get_results(
            include_task=True,
            state='open',
            task_id=task_id
        )

        # in the current setup, only a single result for a single node 
        # in a task exists.
        for task in tasks:
            self.queue.put(task)

    def __sync_task_que_with_server(self):
        """ Get all unprocessed tasks from the server for this node.
        """
        assert self.server_io.cryptor, "Encrpytion has not been setup"

        # make sure we do not add the same job twice. 
        self.queue = queue.Queue()

        # request open tasks from the server
        tasks = self.server_io.get_results(state="open", include_task=True)
        self.log.debug(tasks)
        for task in tasks:
            # try:
            #     task["input"] = self.server_io.cryptor.decrypt_base64(task["input"])
            # except ValueError as e:
            #     self.log.error(
            #         "Unable to decrypt message, assuming it was unencrypted"
            #     )
            self.queue.put(task)
        
        self.log.info(f"received {self.queue._qsize()} tasks" )

    def run_forever(self):
        """ Connect to the server to obtain and execute tasks forever
        """
        try:
            while True:
                # blocking untill a task comes available
                # timeout specified, else Keyboard interupts are ignored
                self.log.info("Waiting for new tasks....")
                while True:
                    try:
                        task = self.queue.get(timeout=1)
                        # if no item is returned, the Empty exception is
                        # triggered, thus break statement is not reached
                        break

                    except queue.Empty:
                        pass

                    except Exception as e:
                        self.log.debug(e)

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
        """ Start a task.
        
            Start the docker image and notify the server that the task 
            has been started. 
            
            :param taskresult: an empty taskresult
        """

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
        # TODO this is not working as this is going though a mount! 
        if (task['database'] 
            and self.config.get('databases') 
            and task['database'] in self.config['databases']):
            database_uri = self.config['databases'][task['database']]
        else:
            database_uri = self.config['databases']["default"]

        # create a temporary volume for each run_id       
        vol_name = self.ctx.docker_temporary_volume_name(task["run_id"])
        self.__docker.create_volume(vol_name)
        
        # start docker container in the background
        if type(taskresult['input']) == dict:
            taskresult['input'] = json.dumps(taskresult['input'])
        self.__docker.run(
            result_id=taskresult["id"], 
            image=task["image"],
            database_uri=database_uri,
            docker_input=taskresult['input'],
            tmp_vol_name=vol_name,
            token=token
        )

    def connect_to_socket(self):
        """ Create long-lasting websocket connection with the server. 

            The connection is used to receive status updates, such as 
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
        self.socket_tasks.set_node_worker(self)

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
        """ Listen for incoming (websocket) messages from the server.

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
        """ Sending messages to central server.
        
            Routine that is in a seperate thread sending results
            to the server when they come available.
        
            TODO change to a single request, might need to reconsider 
                the flow
        """
        
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

            response = self.server_io.request(f"result/{results.result_id}")
            task_id = response.get("task").get("id")
            if not task_id:
                self.log.error(
                    f"task_id of result (id={results.result_id}) "
                    f"could not be retrieved"
                )
                return

            response = self.server_io.request(f"task/{task_id}")
            initiator_id = response.get("initiator")
            if not initiator_id:
                self.log.error(
                    f"Initiator id from task (id={task_id})could not be "
                    f"retrieved"
                )

            self.server_io.patch_results(
                id=results.result_id,
                initiator_id=initiator_id,
                result={
                    'result': results.data,
                    'log': results.logs,
                    'finished_at': datetime.datetime.now().isoformat(),
                }
            )
    
    def __keep_socket_alive(self):
        
        while True:
            time.sleep(60)
            
            # send ping
            self.socket_connected = False  
            self.socket_tasks.emit("ping", self.server_io.whoami.id_)
            
            # wait for pong
            max_waiting_time = 5
            count = 0
            while (not self.socket_connected) and count < max_waiting_time:
                self.log.debug("Waiting for pong")
                time.sleep(1)
                count += 1
            
            if not self.socket_connected:
                self.log.warn("WS seems disconnected, resetting")
                self.socketIO.disconnect()
                self.log.debug("Disconnecting WS")
                self.server_io.refresh_token()
                self.log.debug("Token refreshed")
                self.connect_to_socket()
                self.log.debug("Connected to socket")
                self.__sync_task_que_with_server()


# ------------------------------------------------------------------------------
def run(ctx):
    """ Start the node worker. 
    """
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # initialize node, connect to the server using websockets
    tmc = NodeWorker(ctx)

    # put the node to work, executing tasks that are in the que
    tmc.run_forever()
