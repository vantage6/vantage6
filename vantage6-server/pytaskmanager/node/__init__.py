#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import pathlib
import json
import requests
import time
import datetime
import subprocess
import logging
import jwt
import queue
import docker 

from requests.compat import urljoin
from pprint import pprint
from threading import Thread, Event
from socketIO_client import SocketIO, SocketIONamespace

from pytaskmanager import util
from pytaskmanager.node.DockerManager import DockerManager
from pytaskmanager.node.FlaskIO import ClientNodeProtocol

def name():
    return __name__.split('.')[-1]


class NodeTaskNamespace(SocketIONamespace):
    """Class that handles incoming websocket events."""

    # reference to the node objects, so a callback can edit the 
    # node instance.
    node_worker_ref = None

    def __init__(self, *args, **kwargs):
        """Create a new handler for a socket namespace."""
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger(name())
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

# ------------------------------------------------------------------------------
class NodeWorker(object):
    """Automated node that checks for tasks and executes them."""

    def __init__(self, ctx):
        """Initialize a new TaskMasterNode instance."""
        self.log = logging.getLogger(name())

        self.ctx = ctx
        self.config = ctx.config
        
        # initialize Node connection
        self.flaskIO = ClientNodeProtocol(
            host=self.config.get('server_url'), 
            port=self.config.get('port'),
            path=self.config.get('api_path')
        )

        self.log.info(f"Connecting server: {self.flaskIO.base_path}")

        # Authenticate to the DL server, obtaining a JSON Web Token.
        # Note that self.authenticate() blocks until it succeeds.
        self.log.debug("authenticating")
        self.authenticate()

        # Create a long-lasting websocket connection.
        self.log.debug("creating socket connection with the server")
        self.__connect_to_socket()

        # listen forever for incoming messages, tasks are stored in
        # the queue.
        self.queue = queue.Queue()
        self.log.debug("start thread for incoming messages (tasks)")
        # FIXME: should we be doing this "daemon=True" thing?
        t = Thread(target=self.__listening_worker, daemon=True)
        t.start()

        # check if new tasks were posted while offline.
        self.log.debug("fetching tasks that were posted while offline")
        self.__sync_task_que_with_server() 

        # TODO read allowed repositories from the config file
        self.__docker = DockerManager(
            allowed_repositories=[], 
            tasks_dir=self.ctx.data_dir,
            server_api_url=self.flaskIO.host
        )

        # send results to the server when they come available.
        self.log.debug("Start thread for sending messages (results)")
        # FIXME: should we be doing this "daemon=True" thing?
        t = Thread(target=self.__speaking_worker, daemon=True)
        t.start()

    def authenticate(self):
        """Authenticate with the server using the api-key. If the server
        rejects for any reason we keep trying."""
        api_key = self.config.get("api_key")
        keep_trying = True

        while keep_trying:
            try:
                self.flaskIO.authenticate(api_key)

            except Exception as e:
                msg = 'Authentication failed. Retrying in 10 seconds!'
                self.log.warning(msg)
                self.log.debug(e)
                time.sleep(10)

            else:
                # This is only executed if try-block executed without error.
                keep_trying = False 

        # At this point, we shoud be connnected.
        self.log.info(f"Node name: {self.flaskIO.name}")

    def get_task_and_add_to_queue(self, task_id):
        """Fetches (open) task with task_id from the server. 

        The task_id is delivered by the websocket-connection.
        """

        # fetch (open) result for the node with the task_id
        tasks = self.flaskIO.get_results(
            include_task=True,
            state='open',
            task_id=task_id
        )
        
        # in the current setup, only a single result for a single node 
        # in a task exists.
        for task in tasks:
            self.queue.put(task)

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
    
    def __sync_task_que_with_server(self):
        """Get all unprocessed tasks from the server for this node."""

        # make sure we do not add the same job twice. 
        self.queue = queue.Queue()

        # request open tasks from the server
        tasks = self.flaskIO.get_results(state="open", include_task=True)
        for task in tasks:
            self.queue.put(task)

        self.log.info(f"received {self.queue._qsize()} tasks" )

    def __start_task(self, taskresult):
        """Start the docker image and notify the server that the task 
        has been started."""

        task = taskresult['task']
        self.log.info("Starting task {id} - {name}".format(**task))

        # notify that we are processing this task
        self.flaskIO.set_task_start_time(taskresult["id"])

        # TODO possibly we want to limit the token handout
        token = self.flaskIO.request_token_for_container(
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
            database_uri = self.config['database_uri']

        # start docker container in the background
        self.__docker.run(
            result_id=taskresult["id"], 
            image=task["image"],
            database_uri=database_uri,
            docker_input=task["input"],
            token=token
        )

    def __connect_to_socket(self):
        """Create long-lasting websocket connection with the server. 

        THe connection is used to receive status updates, such as 
        new tasks.
        """
        
        self.socketIO = SocketIO(
            self.flaskIO.host, 
            port=self.flaskIO.port, 
            headers=self.flaskIO.headers,
            wait_for_connection=True
        )
        
        # define() returns the instantiated action_handler 
        namespace = self.socketIO.define(NodeTaskNamespace, '/tasks')
        namespace.setNodeWorker(self)

        # Log the outcome
        if self.socketIO.connected:
            msg = 'connected to host={host} on port={port}'
            msg = msg.format(
                host=self.flaskIO.host, 
                port=self.flaskIO.port
            )
            self.log.info(msg)

        else:
            msg = 'could *not* connect to {host} on port={port}'
            msg = msg.format(
                host=self.flaskIO.host, 
                port=self.flaskIO.port
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
            self.log.info(
                f"Results (id={results.result_id}) are sent to the server!")
            self.flaskIO.patch_results(id=results.result_id, result={
                'result': results.data,
                'log': results.logs,
                'finished_at': datetime.datetime.now().isoformat(),
            })

# ------------------------------------------------------------------------------
def run(ctx):
    """Run the node."""
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # initialize node, connect to the server using websockets
    tmc = NodeWorker(ctx)

    # put the node to work, executing tasks that are in the que
    tmc.run_forever()
