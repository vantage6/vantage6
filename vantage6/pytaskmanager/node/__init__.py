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


module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

class SocketCallBackActions(SocketIONamespace):

    task_master_node_ref = None

    def on_open(self, *args):
        log.debug('on open callback')

    def on_connect(self, *args):
        log.debug('socket connected callback')
        self.emit('enter_rooms')
    
    def on_reconnect(self, *args):
        log.debug('socket reconnected callback')
        self.emit('enter_rooms')

    def on_disconnect(self):
        log.debug('diconnected callback')
        log.info('Disconnected from the server')
    
    def on_message(self, *args):
        log.info(args)
    
    def on_new_task(self, task_id):
        log.debug('new task callback')
        log.info(f'New task is available on the server task_id={task_id}')
        if self.task_master_node_ref:
            self.task_master_node_ref.get_task_and_add_to_queue(task_id)
        else:
            log.critical('Task Master Node reference not set is socket namespace')
        # get_and_execute_tasks()

# ------------------------------------------------------------------------------
class AuthenticationError(Exception):

    def __init__(self, message):
        self.message = message

# ------------------------------------------------------------------------------
class NodeBase(object):
    """Base class for Node and TaskMasterNode."""
    def __init__(self, host, api_path='/api'):

        """Initialize a ClientBase instance."""
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
        url = ''
        if path.startswith('/'):
            url = self._HOST + path
        else:
            url = self._HOST + self._API_PATH + '/' + path

        return url

    def authenticate(self, username=None, password=None, api_key=None):
        """Authenticate with the server as a User or Node.

        Either username and password OR api_key should be provided.
        """
        
        url = self.get_url('token')

        # Infer whether we're authenticating as a user or as a node.
        if username:
            data = {
                'username': username,
                'password': password
            }
        else:
            data = {'api_key': api_key}

        # Request a token from the server.
        response = requests.post(url, json=data)
        response_data = response.json()

        if response.status_code != 200:
            msg = response_data.get('message')
            raise AuthenticationError(msg)

        log.info("Authentication succesful!")

        # Process the response
        self._ACCESS_TOKEN = response_data['access_token']
        self._REFRESH_TOKEN = response_data['refresh_token']
        self._REFRESH_URL = response_data['refresh_url']

        decoded_token = jwt.decode(self._ACCESS_TOKEN, verify=False)
        # log.debug("JWT payload: {}".format(decoded_token))

        return response_data, decoded_token

    def refresh_token(self):
        if self._REFRESH_URL is None:
            raise AuthenticationError('Not authenticated!')

        log.info('Refreshing token')

        url = '{}{}'.format(self._HOST, self._REFRESH_URL)
        response = requests.post(url, headers={'Authorization': 'Bearer ' + self._REFRESH_TOKEN})
        response_data = response.json()

        if response.status_code != 200:
            msg = response_data.get('message')
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
        log.debug(f"{method} | {url}")

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
            msg = response_data.get('message')
            log.warning('Request failed: {}'.format(msg))
            self.refresh_token()
            log.info('Retrying ...')
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
class Node(NodeBase):
    """Class for communicating with the server in custom scripts."""
    pass

# ------------------------------------------------------------------------------
class TaskMasterNode(NodeBase):
    """Automated node that checks for tasks and executes them."""

    def __init__(self, ctx):
        """Initialize a new TaskMasterNode instance."""

        self.log = logging.getLogger(__name__)

        self.ctx = ctx
        self.name = None
        self.config = None

        # if context is provided load enviroment settings
        # TODO is this correct? in case no ctx is provided
        # this will fail, right?
        if ctx:
            self.name = ctx.instance_name
            self.config = ctx.config['env']

        super().__init__(
            self.config['server_url'], 
            self.config['api_path']
        )

        self.node_id = None
        self.log.info(f"Using server: {self._HOST}")

        # Authenticate to the DL server, obtaining a JWT
        # authorization token.
        log.debug("authenticating")
        self.authenticate()

        # Create a long-lasting websocket connection.
        log.debug("create socket connection with the server")
        self.connect_to_socket(action_handler=SocketCallBackActions)

        # listen forever for incomming messages, tasks are stored in
        # the queue.
        self.queue = queue.Queue()
        log.debug("start thread for incomming messages (tasks)")
        t = Thread(target=self.__listening_worker, daemon=True)
        t.start()

        # check if new tasks were posted while offline.
        log.debug("fetching tasks that were posted while offline")
        self.sync_task_que_with_server()  # adds them to queue

    def authenticate(self):
        """Authenticate with the server using the api-key."""
        authenticated = False
        while not authenticated:
            try:
                response_data, decoded_token = super().authenticate(
                    api_key=self.config['api_key'])
                authenticated = True
            except Exception as e:
                self.log.warning('Connection refused by server, server might be offline')
                self.log.info('trying again in 10 seconds')
                self.log.debug(e)
                time.sleep(10)
        
        self.node_id = decoded_token['identity']
        node = self.request(response_data['node_url'])
        
        log.info("Node name: '{name}'".format(**node))

    def sync_task_que_with_server(self):
        """Get all unprocessed tasks from the server"""

        url = f'result?state=open&include=task&node_id={self.node_id}'

        for task in self.request(url):
            self.queue.put(task)

        self.log.info(f"there are {self.queue._qsize()} new tasks since last time" )

    def get_task_and_add_to_queue(self, task_id):
        url = f'result?state=open&include=task&task_id={task_id}&node_id={self.node_id}'
        tasks = self.request(url)
        # FIXME this should only be a single task
        for task in tasks:
            self.queue.put(task)

    def execute_task(self, taskresult):
        """
        Execute a single task and uploads result to server.

        :param taskresult: dict that contains the (empty) result details as well
                           as the details of the task itself.
        :raises Exception: raises an exception if ... 
        """
        task = taskresult['task']

        log.info("-" * 80)
        log.info("Starting task {id} - {name}".format(**task))
        log.info("-" * 80)

        # notify the server we've started the task. 
        result_data = {
            'started_at': datetime.datetime.now().isoformat(),
        }
        path = taskresult['_id']
        response = self.request(path, json_data=result_data, method='patch')
        log.debug(f"server response = {response}")

        # create directory to put files into
        task_dir = self.make_task_dir(task)

        # pull the image for updates or download
        self.docker_pull(task['image'])

        # Files are used for input and output
        inputFilePath = os.path.join(task_dir, "input.txt")
        outputFilePath = os.path.join(task_dir, "output.txt")

        result_text, log_data = self.docker_run(task, inputFilePath, outputFilePath)

        result_data = {
            'result': result_text,
            'log': log_data,
            'finished_at': datetime.datetime.now().isoformat(),
        }

        # Do an HTTP PATCH to send back result (response)
        log.info('PATCHing result to server')
        response = self.request(path, json_data=result_data, method='patch')
        log.debug(f"server response = {response}")

        log.info("-" * 80)
        log.info("Finished task {id} - {name}".format(**task))
        log.info("-" * 80)
        log.info('')

    def make_task_dir(self, task):
        task_dir = self.ctx.get_file_location('data', "task-{0:09d}".format(task['id']))
        log.info("Using '{}' for task".format(task_dir))
        if os.path.exists(task_dir):
            log.warning("Task directory already exists: '{}'".format(task_dir))

        else:
            try:
                os.makedirs(task_dir)
            except Exception as e:
                log.error("Could not create task directory: {}".format(task_dir))
                log.exception(e)
                raise

        return task_dir

    def docker_pull(self, image):
        
        cmd = "docker pull " + image

        log.info(f"Pulling latest version of docker image '{image}'")
        log.info(f"Command: '{cmd}'")
        
        p = subprocess.Popen(cmd, subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        out, err = p.communicate()
        
        log.info(out)
        log.debug(err)

    def docker_run(self, task, inputFilePath, outputFilePath):
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
                log.warning("'{}' is not a file!".format(self.config['database_uri']))
        else:
            log.warning('no database file specified')


        dockerParams += "-e DATABASE_URI=%s " % DATABASE_URI

        dockerParams += "--add-host dockerhost:%s" % self.config['docker_host']

        dockerExecLine = "docker run  " + dockerParams + ' ' + task['image']
        log.info("Executing docker: {}".format(dockerExecLine))

        # FIXME: consider using subprocess.run(...)
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

    def connect_to_socket(self, action_handler=None):
        headers = {
            "Authorization": f"Bearer {self._ACCESS_TOKEN}",
        }
        # TODO we need to split host and port from the start
        host_and_port = self._HOST.split(':')
        host = host_and_port[0]+':'+host_and_port[1]
        port = int(host_and_port[2])
        
        self.socketIO = SocketIO(
            host, 
            port=port, 
            Namespace=action_handler,
            headers=headers,
            wait_for_connection=True
        )
        
        if self.socketIO.connected:
            self.log.info(f'connected to host <{host}> on port <{port}>')
        else:
            self.log.critical(f'could not connect to <{host}> on port <{port}>')
        
    def run_forever(self):
        """Connect to the server to obtain and execute tasks forever"""
        
        while True:
            # blocking untill a task comes available
            task = self.queue.get()
            self.execute_task(task)
    
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
    SocketCallBackActions.task_master_node_ref = tmc

    # put the node to work, executing tasks that are in the que
    tmc.run_forever()




