#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

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


class NodeNamespace(SocketIONamespace):
    """Class that handles incomming websocket events."""

    # reference to the node objects, so a call-back can edit the 
    # node instance.
    node_worker_ref = None

    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger(name())
        super().__init__(*args, **kwargs)

    def on_disconnect(self):
        """Call-back when the server disconnects."""

        self.log.debug('diconnected callback')
        self.log.info('Disconnected from the server')
    
    def on_new_task(self, task_id):
        """Call back to fetch new available tasks."""

        if self.node_worker_ref:
            self.node_worker_ref.get_task_and_add_to_queue(task_id)
            self.log.info(f'New task has been added task_id={task_id}')
        else:
            self.log.critical('Task Master Node reference not set is socket namespace')


# ------------------------------------------------------------------------------
class NodeBase(object):
    """Base class for Node and Node. Provides the interface to the
    ppDLI server."""
    
    def __init__(self, host='localhost', port=5000, api_path='/api'):
        """Initialize a ClientBase instance."""
        self.log = logging.getLogger(name())
        
        # initialize Node connection
        self.flaskIO = ClientNodeProtocol(
            host=host, 
            port=port, 
            path=api_path
        )


# ------------------------------------------------------------------------------
class NodeWorker(NodeBase):
    """Automated node that checks for tasks and executes them."""

    def __init__(self, ctx):
        """Initialize a new TaskMasterNode instance."""

        self.ctx = ctx
        self.config = ctx.config

        super().__init__(
            host=self.config.get('server_url'), 
            port=self.config.get('port'),
            api_path=self.config.get('api_path')
        )

        self.log.info(f"Connecting server: {self.flaskIO.base_path}")

        # Authenticate to the DL server, obtaining a JWT
        # authorization token.
        self.log.debug("authenticating")
        self.authenticate()

        # Create a long-lasting websocket connection.
        self.log.debug("create socket connection with the server")
        self.__connect_to_socket(action_handler=NodeNamespace)

        # listen forever for incomming messages, tasks are stored in
        # the queue.
        self.queue = queue.Queue()
        self.log.debug("start thread for incomming messages (tasks)")
        t = Thread(target=self.__listening_worker, daemon=True)
        t.start()

        # check if new tasks were posted while offline.
        self.log.debug("fetching tasks that were posted while offline")
        self.__sync_task_que_with_server() 

        # TODO read allowed repositories from the config file
        self.__docker = DockerManager(
            allowed_repositories=[], tasks_dir=self.ctx.data_dir)

        # send results to the server when they come available.
        self.log.debug("Start thread for sending messages (results)")
        t = Thread(target=self.__speaking_worker, daemon=True)
        t.start()

    def authenticate(self):
        """Authenticate with the server using the api-key. If the server
        rejects for any reason we keep trying."""
        
        while True:
            try:
                self.flaskIO.authenticate(api_key=self.config.get("api_key"))
                break # authenticated, leave loop
            except Exception as e:
                self.log.warning('Connection refused by server, server might be offline. Retrying in 10 seconds!')
                self.log.debug(e)
                time.sleep(10)
        
        self.log.info(f"Node name: {self.flaskIO.name}")

    def get_task_and_add_to_queue(self, task_id):
        
        # fetch (open) result for the node with the task_id
        tasks = self.flaskIO.get_results(
            include_task=True,
            state='open',
            task_id=task_id
        )
        
        # in the current setup, only a single result for a single node in a task exists.
        for task in tasks:
            self.queue.put(task)

    def run_forever(self):
        """Connect to the server to obtain and execute tasks forever"""
        
        try:
            while True:
                # blocking untill a task comes available
                # time out specified, else Keyboard interupts are ignored
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
            self.log.debug("Catched a keyboard interupt, gracefully shutting down...")
            self.socketIO.disconnect()
            sys.exit()
    
    def __sync_task_que_with_server(self):
        """Get all unprocessed tasks from the server."""

        # make sure we do not add the same job twice. 
        self.queue = queue.Queue()

        # request open tasks from the server
        tasks = self.flaskIO.get_results(state="open",include_task=True)
        for task in tasks:
            self.queue.put(task)

        self.log.info(f"received {self.queue._qsize()} tasks" )

    def __start_task(self, taskresult):
        """
        """

        task = taskresult['task']
        self.log.info("Starting task {id} - {name}".format(**task))

        # notify that we are processing this task
        self.flaskIO.set_task_start_time(taskresult['id'])

        # start docker container in the background
        self.__docker.run(taskresult["id"], task["image"], task["input"])


    def __connect_to_socket(self, action_handler=None):
        
        self.socketIO = SocketIO(
            self.flaskIO.host, 
            port=self.flaskIO.port, 
            headers=self.flaskIO.headers,
            wait_for_connection=True
        )
        
        self.socketIO.define(action_handler, '/tasks')
        
        if self.socketIO.connected:
            self.log.info(f'connected to host={self.flaskIO.host} \
                on port={self.flaskIO.port}')
        else:
            self.log.critical(f'could not connect to {self.flaskIO.host} on \
                port <{self.flaskIO.port}>')
        
    def __listening_worker(self):
        """Routine that is in a seperate thread and listens for
        incomming messages from the server"""
        
        self.log.debug("Listening for incomming messages")
        while True:
            # incomming messages are handled by the action_handler instance which 
            # is attached when the socked connection was made. wait is blocking 
            # forever (if no time is specified).
            self.socketIO.wait()

    def __speaking_worker(self):
        """Routine that is in a seperate thread sending results
        to the server when they come available."""
        
        self.log.debug("Waiting for results to send to the server")

        while True:
            results = self.__docker.get_result()
            self.log.info(f"Results from result {results.result_id} are send to the server!")
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

    # reference to tmc in to give call-back functions
    # access to the node methods.
    NodeNamespace.node_worker_ref = tmc

    # put the node to work, executing tasks that are in the que
    tmc.run_forever()
