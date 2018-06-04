#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys, os
import pathlib

import json
import requests
from requests.compat import urljoin

import time, datetime
import subprocess

import logging
import jwt
from pprint import pprint

from pytaskmanager import util


module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


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
        # url = '{}/api/token'.format(self._HOST)
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

        if method == 'put':
            response = requests.put(url, json=json_data, headers=headers)
        elif method == 'post':
            response = requests.post(url, json=json_data, headers=headers)
        else:
            response = requests.get(url, headers=headers)

        response_data = response.json()

        if response.status_code != 200:
            msg = response_data.get('message')
            log.warning('Request failed: {}'.format(msg))
            self.refresh_token()
            log.info('Retrying ...')
            return self.request(path, json_data, method)

        return response_data

    def get_collaboration(self, collaboration_id=None):
        if collaboration_id:
            return self.request('/collaboration/{}'.format(collaboration_id))

        return self.request('/collaboration')

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

        if ctx:
            self.name = ctx.instance_name
            self.config = ctx.config['app']

        super().__init__(
            self.config['server_url'], 
            self.config['api_path']
        )

        self.node_id = None
        self.log.info("Using server: {}".format(self._HOST))

    def authenticate(self):
        """Authenticate with the server using the api-key."""
        response_data, decoded_token = super().authenticate(api_key=self.config['api_key'])
        self.node_id = decoded_token['identity']
        node = self.request(response_data['node_url'])
        log.info("Node name: '{name}'".format(**node))

    def get_tasks(self):
        """Retrieve a list of tasks from the server."""
        url = '/result?state=open&include=task&node_id={node_id}'
        url = url.format(node_id=self.node_id)

        return self.request(url)

    def get_and_execute_tasks(self):
        """
        Continuously check for tasks and execute them.

        A list of tasks for a node actually consists of a list of (empty)
        task *results* that are (pre)created by the server. This allows the
        server to keep track of unfinished tasks.
        """

        # Get tasks actually returns a list of taskresults where
        # result == null
        taskresults = self.get_tasks()

        log.info("Received {} task(s)".format(len(taskresults)))

        try:
            for taskresult in taskresults:
                self.execute_task(taskresult)
                
        except Exception as e:
            log.exception(e)

        # Sleep 10 seconds
        log.debug("Sleeping {} second(s)".format(self.config['delay']))
        time.sleep(self.config['delay'])

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

        # Notify the server we've started .. 
        result_data = {
            'started_at': datetime.datetime.now().isoformat(),
        }

        path = taskresult['_id']
        response = self.request(path, json_data=result_data, method='put')
        # log.debug(response)

        
        # Create directory to put files into
        task_dir = self.make_task_dir(task)

        # Pull the image for updates or download
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

        # Do an HTTP PUT to send back result (response)
        log.info('PUTing result to server')
        response = self.request(path, json_data=result_data, method='put')

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

        log.info("Pulling latest version of docker image '{}'".format(image))
        log.info("Command: '{}'".format(cmd))
        p = subprocess.Popen(cmd, subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        out, err = p.communicate()
        log.info(out)

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

        if pathlib.Path(self.config['database_uri']).is_file():
            dockerParams += "-v " + DATABASE_URI.replace(' ', '\ ') + ":/app/database " # mount data store
            DATABASE_URI = "/app/database"
        else:
            print("*** warning ***")
            print("'{}' is not a file!".format(self.config['database_uri']))

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

    def run_forever(self):
        """Run!"""
        interval = 30

        while True:
            try:
                self.authenticate()

                while True:
                    self.get_and_execute_tasks()
            except requests.exceptions.ConnectionError as e:
                log.error("Could not connect to server!")
                log.error(e)
                log.info("Wating {} seconds before trying again".format(interval))
                time.sleep(interval)

# ------------------------------------------------------------------------------
def run(ctx):
    """Run the node."""
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    tmc = TaskMasterNode(ctx)
    tmc.run_forever()



