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
from threading import Thread
from socketIO_client import SocketIO, SocketIONamespace

from pytaskmanager import util

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
class AuthenticationError(Exception):

    def __init__(self, message):
        self.message = message

# ------------------------------------------------------------------------------
class NodeBase(object):
    """Base class for Node and TaskMasterNode. Provides the interface to the
    ppDLI server."""
    
    def __init__(self, host, api_path='/api'):
        """Initialize a ClientBase instance."""

        self.log = logging.getLogger(name())

        self._HOST = host

        if api_path.endswith('/') and len(api_path) > 1:
            self._API_PATH = self._API_PATH.rstrip('/')
        elif api_path:
            self._API_PATH = api_path
        else:
            self._API_PATH = '/'

        self._REFRESH_URL = None
        self._ACCESS_TOKEN = None
        self._REFRESH_TOKEN = None

    def get_url(self, path):
        return self._HOST + path if path.startswith('/') else \
          self._HOST + self._API_PATH + '/' + path 
        
    def authenticate(self, api_key=None):
        """Authenticate with the server as a Node."""

        # get url where token can be obtained.
        url = self.get_url('token')

        # request a token from the server.
        response = requests.post(url, json={'api_key': api_key})
        response_data = response.json()

        # handle authentication problems
        if response.status_code != 200:
            msg = response_data.get('msg')
            raise AuthenticationError(msg)
        self.log.info("Authenticated")

        # Process the response
        self._ACCESS_TOKEN = response_data['access_token']
        self._REFRESH_TOKEN = response_data['refresh_token']
        self._REFRESH_URL = response_data['refresh_url']

        decoded_token = jwt.decode(self._ACCESS_TOKEN, verify=False)
        
        return response_data, decoded_token

    def refresh_token(self):
        if self._REFRESH_URL is None:
            raise AuthenticationError('Not authenticated!')

        self.log.info('Refreshing token')

        url = '{}{}'.format(self._HOST, self._REFRESH_URL)
        response = requests.post(url, headers={'Authorization': 'Bearer ' + self._REFRESH_TOKEN})
        response_data = response.json()

        if response.status_code != 200:
            msg = response_data.get('msg')
            raise AuthenticationError(msg)

        self._ACCESS_TOKEN = response_data['access_token']

    def request(self, path, json_data=None, method='get'):
        """Performs a PUT by default is json_data is provided without method."""
        method = method.lower()

        if json_data and method == 'get':
            method = 'put'

        headers = {
            'Authorization': 'Bearer ' + self._ACCESS_TOKEN,
        }

        url = self.get_url(path)
        self.log.debug(f"{method} | {url}")

        if method == 'put':
            response = requests.put(url, json=json_data, headers=headers)
        elif method=='patch':
            response = requests.patch(url, json=json_data, headers=headers)
        elif method == 'post':
            response = requests.post(url, json=json_data, headers=headers)
        else:
            response = requests.get(url, headers=headers)

        response_data = response.json()

        # TODO only do this when token is expired!
        if response.status_code != 200:
            msg = response_data.get('msg')
            self.log.warning('Request failed: {}'.format(msg))
            self.refresh_token()
            self.log.info('Retrying ...')
            return self.request(path, json_data, method)

        return response_data

    def get_collaboration(self, collaboration_id=None):
        if collaboration_id:
            return self.request('collaboration/{}'.format(collaboration_id))

        return self.request('collaboration')

    def get_task(self, task_id, include=''):
        url = 'task/{}?include={}'.format(task_id, include)
        return self.request(url)

    def create_task(self, name, image, collaboration_id,  input_='', description=''):
        task = {
            "name": name,
            "image": image, 
            "collaboration_id": collaboration_id,
            "input": input_,
            "description": description,
        }        

        return self.request('task', json_data=task, method='post')


# ------------------------------------------------------------------------------
class TaskMasterNode(NodeBase):
    """Automated node that checks for tasks and executes them."""

    def __init__(self, ctx):
        """Initialize a new TaskMasterNode instance."""

        self.ctx = ctx
        self.name = ctx.instance_name
        self.config = ctx.config

        super().__init__(
            self.config['server_url'], 
            self.config['api_path']
        )

        self.node_id = None
        self.log.info(f"Using server: {self._HOST}")

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
                response_data, decoded_token = super().authenticate(
                    api_key=self.config['api_key'])
                break # authenticated, leave loop
            except Exception as e:
                self.log.warning('Connection refused by server, server might be offline')
                self.log.info('trying again in 10 seconds')
                self.log.debug(e)
                time.sleep(10)
        
        self.node_id = decoded_token['identity']

        node = self.request(response_data['node_url'])
        self.log.info("Node name: '{name}'".format(**node))

    def get_task_and_add_to_queue(self, task_id):
        
        # fetch (empty) result for the node with the task_id
        url = f'result?state=open&include=task&task_id={task_id}&node_id={self.node_id}'
        tasks = self.request(url)

        # in the current setup, only a single result for a single node in a task exists.
        for task in tasks:
            self.queue.put(task)

    def run_forever(self):
        """Connect to the server to obtain and execute tasks forever"""
        
        while True:
            # blocking untill a task comes available
            task = self.queue.get()
            try:
                self.__execute_task(task)
            except Exception as e:
                self.log.exception(e)

    
    def __sync_task_que_with_server(self):
        """Get all unprocessed tasks from the server"""

        # make sure we do not add the same job twice. 
        self.queue = queue.Queue()

        # request open tasks from the server
        url = f'result?state=open&include=task&node_id={self.node_id}'
        for task in self.request(url):
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

        # notify the server we've started the task. 
        result_data = {
            'started_at': datetime.datetime.now().isoformat(),
        }
        path = taskresult['_id']
        response = self.request(path, json_data=result_data, method='patch')
        self.log.debug(f"server response = {response}")

        # create directory to put files into
        task_dir = self.__make_task_dir(task)

        # pull the image for updates or download
        self.__docker_pull(task['image'])

        # Files are used for input and output
        inputFilePath = os.path.join(task_dir, "input.txt")
        outputFilePath = os.path.join(task_dir, "output.txt")

        result_text, log_data = self.__docker_run(task, inputFilePath, outputFilePath)

        result_data = {
            'result': result_text,
            'log': log_data,
            'finished_at': datetime.datetime.now().isoformat(),
        }

        # Do an HTTP PATCH to send back result (response)
        self.log.info('PATCHing result to server')
        response = self.request(path, json_data=result_data, method='patch')
        self.log.debug(f"server response = {response}")

        self.log.info("-" * 80)
        self.log.info("Finished task {id} - {name}".format(**task))
        self.log.info("-" * 80)
        self.log.info('')

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
        headers = {
            "Authorization": f"Bearer {self._ACCESS_TOKEN}",
        }
        
        # seperate host and port.
        host_and_port = self._HOST.split(':')
        host = host_and_port[0]+':'+host_and_port[1]
        port = int(host_and_port[2])
        
        # establish connection.
        self.socketIO = SocketIO(
            host, 
            port=port, 
            # Namespace=action_handler,
            headers=headers,
            wait_for_connection=True
        )
        
        event_namespace = self.socketIO.define(action_handler, '/tasks')


        if self.socketIO.connected:
            self.log.info(f'connected to host <{host}> on port <{port}>')
        else:
            self.log.critical(f'could not connect to <{host}> on port <{port}>')
        
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
    tmc = TaskMasterNode(ctx)

    # reference to tmc in to give call-back functions
    # access to the node methods.
    NodeNamespace.task_master_node_ref = tmc

    # put the node to work, executing tasks that are in the que
    tmc.run_forever()




