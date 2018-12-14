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

from requests.compat import urljoin
from pprint import pprint
from threading import Thread, Event
from socketIO_client import SocketIO, SocketIONamespace

from pytaskmanager import util
from pytaskmanager.node.FlaskIO import ClientNodeProtocol

def name():
    return __name__.split('.')[-1]


class NodeNamespace(SocketIONamespace):
    """Class that handles incomming websocket events."""

    # reference to the node objects, so a call-back can edit the 
    # node instance.
    task_master_node_ref = None

    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger(name())
        super().__init__(*args, **kwargs)

    def on_disconnect(self):
        """Call-back when the server disconnects."""

        self.log.debug('diconnected callback')
        self.log.info('Disconnected from the server')
    
    def on_new_task(self, task_id):
        """Call back to fetch new available tasks."""

        if self.task_master_node_ref:
            self.task_master_node_ref.get_task_and_add_to_queue(task_id)
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
                    
                try:
                    self.__execute_task(task)
                except Exception as e:
                    self.log.exception(e)

        except KeyboardInterrupt:
            self.log.debug("Catched a keyboard interupt, gracefully shutting down...")
            self.socketIO.disconnect()
            sys.exit()
    
    def __sync_task_que_with_server(self):
        """Get all unprocessed tasks from the server"""

        # make sure we do not add the same job twice. 
        self.queue = queue.Queue()

        # request open tasks from the server
        tasks = self.flaskIO.get_results(state="open",include_task=True)
        for task in tasks:
            self.queue.put(task)

        self.log.info(f"received {self.queue._qsize()} tasks" )

    def __execute_task(self, taskresult):
        """
        Execute a single task and uploads result to server.

        :param taskresult: dict that contains the (empty) result details as well
                           as the details of the task itself.
        :raises Exception: raises an exception if ... 
        """
        task = taskresult['task']

        self.log.info("-" * 80)
        self.log.info("Starting task {id} - {name}".format(**task))
        self.log.info("-" * 80)

        # notify that we are processing this task
        self.flaskIO.set_task_start_time(taskresult['id'])

        # create directory to put files into
        task_dir = self.__make_task_dir(task)

        # pull the image for updates or download
        self.__docker_pull(task['image'])

        # Files are used for input and output
        inputFilePath = os.path.join(task_dir, "input.txt")
        outputFilePath = os.path.join(task_dir, "output.txt")

        # execute algorithm 
        result_text, log_data = self.__docker_run(task, inputFilePath, outputFilePath)

        # Do an HTTP PATCH to send back result (response)
        self.flaskIO.patch_results(id=taskresult['id'], result={
            'result': result_text,
            'log': log_data,
            'finished_at': datetime.datetime.now().isoformat(),
        })
        
        self.log.info("-" * 80)
        self.log.info("Finished task {id} - {name}".format(**task))
        self.log.info("-" * 80)

    def __make_task_dir(self, task):
        task_dir = self.ctx.get_file_location('data', "task-{0:09d}".format(task['id']))
        self.log.info("Using '{}' for task".format(task_dir))
        if os.path.exists(task_dir):
            self.log.warning("Task directory already exists: '{}'".format(task_dir))

        else:
            try:
                os.makedirs(task_dir)
            except Exception as e:
                self.log.error("Could not create task directory: {}".format(task_dir))
                self.log.exception(e)
                raise

        return task_dir

    def __docker_pull(self, image):
        
        cmd = "docker pull " + image
        self.log.info(f"Pulling latest version of docker image '{image}'")
        self.log.info(f"Command: '{cmd}'")
        
        p = subprocess.Popen(cmd, subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        out, err = p.communicate()
        
        self.log.info(out)
        self.log.debug(err)

    def __docker_run(self, task, inputFilePath, outputFilePath):
        """
        Run the docker container for the task and provide it with IO.

        :param task: dict containing the task details
        :param inputFilePath: path to the file used for input
        :param outputFilePath: path to the file used for output
        :returns: tuple of output (contents of outputFilePath after execution) 
                  and STDOUT
        :raises Exception: raises an exception if docker cannot be run.
        """
        # FIXME: need to check for running docker daemon and/or other error messages!
        # FIXME: switch to package 'docker' instead

        # Prepare files for input/output.
        with open(inputFilePath, 'w') as fp:
            fp.write(task['input'] or '')
            fp.write('\n')

        with open(outputFilePath, 'w') as fp:
            fp.write('')


        # Prepare shell statement for running the docker image
        dockerParams  = "--rm " # container should be removed after execution
        # TODO let's docker!
        dockerParams += "-v " + inputFilePath.replace(' ', '\ ') + ":/app/input.txt "   # mount input file
        dockerParams += "-v " + outputFilePath.replace(' ', '\ ') + ":/app/output.txt " # mount output file

        DATABASE_URI = self.config['database_uri']

        if DATABASE_URI:
            if pathlib.Path(self.config['database_uri']).is_file():
                dockerParams += "-v " + DATABASE_URI.replace(' ', '\ ') + ":/app/database " # mount data store
                DATABASE_URI = "/app/database"
            else:
                self.log.warning("'{}' is not a file!".format(self.config['database_uri']))
        else:
            self.log.warning('no database file specified')


        dockerParams += "-e DATABASE_URI=%s " % DATABASE_URI

        dockerParams += "--add-host dockerhost:%s" % self.config['docker_host']

        dockerExecLine = "docker run  " + dockerParams + ' ' + task['image']
        self.log.info("Executing docker: {}".format(dockerExecLine))

        # FIXME: consider using subprocess.run(...)
        #        or use the python package that provides an API for docker
        # https://docs.python.org/3/library/subprocess.html#module-subprocess
        p = subprocess.Popen(dockerExecLine, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        # This blocks until the process finishes.
        out, err = p.communicate()
        log_data = out.decode("utf-8") # + "\r\n" + err.decode("utf-8") 
        # log.info(log_data)

        if p.returncode:
            raise Exception('did not succeed in running docker!?')


        with open(outputFilePath) as fp:
            result_text = fp.read()
            # log.info(result_text)

        return result_text, log_data

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
        """routine that is in a seperate thread and listens for
        incomming messages from the server"""
        
        self.log.debug("listening for incomming messages")
        while True:
            # incomming messages are handled by the action_handler instance which 
            # is attached when the socked connection was made. wait is blocking 
            # forever (if no time is specified).
            self.socketIO.wait()

# ------------------------------------------------------------------------------
def run(ctx):
    """Run the node."""

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # initialize node, connect to the server using websockets
    tmc = NodeWorker(ctx)

    # reference to tmc in to give call-back functions
    # access to the node methods.
    NodeNamespace.task_master_node_ref = tmc

    # put the node to work, executing tasks that are in the que
    tmc.run_forever()
