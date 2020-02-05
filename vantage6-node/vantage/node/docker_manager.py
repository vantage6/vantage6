""" Docker manager

The docker manager is responsible for communicating with the docker-
deamon and is a wrapper arround the docker module. It has methods
for creating docker networks, docker volumes, start containers
and retreive results from finisched containers

TODO the task folder is also created by this class. This folder needs
to be cleaned at some point.
"""
import time
import logging
import docker
import os
import pathlib
import re

from typing import NamedTuple

import vantage.constants as cs

from vantage.util import logger_name

class Result(NamedTuple):
    """ Data class to store the result of the docker image.
    """
    result_id: int
    logs: str
    data: str
    status_code: int

class DockerManager(object):
    """ Wrapper for the docker module, to be used specifically for vantage.
    
        It handles docker images names to results `run(image)`. It manages 
        docker images, files (input, output, token, logs). Docker images run 
        in detached mode, which allows to run multiple docker containers at 
        the same time. Results (async) can be retrieved through 
        `get_result()` which returns the first available result.
    """

    log = logging.getLogger(logger_name(__name__))
    
    # TODO validate that allowed repositoy is used
    # TODO authenticate to docker repository... from the config-file

    def __init__(self, allowed_images, tasks_dir, 
        docker_socket_path, isolated_network_name: str) -> None:
        """ Initialization of DockerManager creates docker connection and
            sets some default values.
            
            :param allowed_repositories: allowed urls for docker-images. 
                Empty list implies that all repositoies are allowed.
            :param tasks_dir: folder to store task related data.
        """
        self.log.debug("Initializing DockerManager")
        self.__tasks_dir = tasks_dir

        # Connect to docker deamon
        self.client = docker.DockerClient(base_url=docker_socket_path)

        # keep track of the running containers
        self.active_tasks = []

        # TODO this still needs to be checked
        self._allowed_images = allowed_images
        
        # create / get isolated network to which algorithm containers 
        # can attach
        self.isolated_network = \
            self.create_isolated_network(isolated_network_name)
    
    def create_isolated_network(self, name: str) \
        -> docker.models.networks.Network:
        """ Creates an internal (docker) network 
        
            Used by algorithm containers to communicate with the node API.

            :param name: name of the internal network
        """
        try:
            network = self.client.networks.get(name)
            self.log.debug(f"Network {name} already exists.")
        except:
            self.log.debug(f"Creating isolated docker-network {name}")
            network = self.client.networks.create(
                name, 
                driver="bridge",
                internal=False,
                scope="local"
            )

        return network

    def create_volume(self, volume_name: str):
        """ Create a temporary volume for a single run.

            A single run can consist of multiple algorithm containers. 
            It is important to note that all algorithm containers having 
            the same run_id have access to this container.

            :param run_id: integer representing the run_id
        """
        try:
            self.client.volumes.get(volume_name)
            self.log.debug(f"Volume {volume_name} already exists.")
        except docker.errors.NotFound:
            self.log.debug(f"Creating volume {volume_name}")
            self.client.volumes.create(volume_name)

    def is_docker_image_allowed(self, docker_image_name: str):
        """ Checks the docker image name.

            Against a list of regular expressions as defined in the 
            configuration file. If no expressions are defined, all 
            docker images are accepted.

            :param docker_image_name: uri to the docker image
        """

        # if no limits are declared
        if not self._allowed_images:
            self.log.warn("All docker images are allowed on this Node!")
            return True

        # check if it matches any of the regex cases
        for regex_expr in self._allowed_images:
            expr_ = re.compile(regex_expr)
            if expr_.match(docker_image_name):
                return True

        # if not, it is considered an illegal image
        return False

    def run(self, result_id: int,  image: str, database_uri: str, 
        docker_input: bytes, tmp_vol_name: int, token: str) -> bool:
        """ Runs the docker-image in detached mode.

            It will will attach all mounts (input, output and datafile)
            to the docker image. And will supply some environment
            variables.
        
            :param result_id: server result identifyer
            :param image: docker image name
            :param database_uri: URI of data file
            :param docker_input: input that can be read by docker container
            :param run_id: identifieer of the run sequence
            :param token: Bearer token that the container can use
        """

        # verify that an allowed image is used
        if not self.is_docker_image_allowed(image):
            self.log.critical(
                f"Docker image {image} is not allowed on this Node!")
            return False

        # create I/O files for docker
        self.log.debug("prepare IO files in docker volume")
        io_files = [
            ('input', docker_input), 
            ('output', b''), 
            ('token', token.encode("ascii")), 
        ]
        
        # the data-volume is shared amongst all algorithm containers,
        # therefore there should be no sensitive information in here. 
        # FIXME ideally we should have a seperate mount/volume for this
        # this was not possible yet as mounting volumes from containers
        # is terrible when working from windows (as you have to convert
        # from windows to unix sevral times...). This is a potential leak
        # as containers might access other container keys, which allows
        # them to post tasks in different collaborations.
        folder_name = "task-{0:09d}".format(result_id)
        io_path = pathlib.Path("/mnt/data-volume") / folder_name
        os.makedirs(io_path, exist_ok=True)
        for (filename, contents) in io_files:
            path = io_path / f"{filename}"
            with open(path, 'wb') as fp:
                fp.write(contents)

        # attempt to pull the latest image
        try:
            self.log.info(f"Retrieving latest image={image}")
            self.client.images.pull(image)
        except Exception as e:
            self.log.error(e)
        
        # define enviroment variables for the docker-container, the 
        # host, port and api_path are from the local proxy server to 
        # facilitate indirect communication with the central server
        tmp_folder = "/mnt/tmp" # docker env
        environment_variables = {
            "INPUT_FILE": str(io_path / "input"),
            "OUTPUT_FILE": str(io_path / "output"),
            "TOKEN_FILE": str(io_path / "token"),
            "TEMPORARY_FOLDER": tmp_folder,
            "DATABASE_URI": "/mnt/data-volume/database.csv",
            "HOST": f"http://{cs.NODE_PROXY_SERVER_HOSTNAME}",
            "PORT": os.environ["PROXY_SERVER_PORT"],
            "API_PATH": "",
        }
        self.log.debug(f"Environment={environment_variables}")

        # attempt to run the image
        try:
            self.log.info(f"Run docker image={image}")
            container = self.client.containers.run(
                image, 
                detach=True, 
                environment=environment_variables,
                network=self.isolated_network.name,
                volumes={
                    tmp_vol_name:{
                        "bind":tmp_folder,
                        "mode": "rw"
                    },
                    os.environ["DATA_VOLUME_NAME"]:{
                        "bind": "/mnt/data-volume", 
                        "mode": "rw"
                    }
                }
            )
        except Exception as e:
            self.log.debug(e)
            return False

        # keep track of the container
        self.active_tasks.append({
            "result_id": result_id,
            "container": container,
            "output_file": io_path / "output"
        })

        return True

    def get_result(self):
        """ Returns the oldest (FIFO) finished docker container.
        
            This is a blocking method until a finished container shows up.
            Once the container is obtained and the results are red, the 
            container is removed from the docker environment.
        """

        # get finished results and get the first one, if no result is available 
        # this is blocking
        finished_tasks = []
        while not finished_tasks:
            self.__refresh_container_statuses()
            
            finished_tasks = [t for t in self.active_tasks \
                if t['container'].status == 'exited']
            
            time.sleep(1)
        
        # at least one task is finished
        finished_task = finished_tasks.pop()

        self.log.debug(
            f"Result id={finished_task['result_id']} is finished"
        )
        
        # report if the container has a different status than 0
        status_code = finished_task["container"].attrs["State"]["ExitCode"]
        if status_code:
            self.log.error(f"Received not 0 exitcode={status_code}")

        # get all info from the container and cleanup
        container = finished_task["container"]
        
        log = container.logs().decode('utf8')

        try:
            container.remove()
        except Exception as e:
            self.log.error(f"Failed to remove container {container.name}")
            self.log.debug(e)

        self.active_tasks.remove(finished_task)
        
        # retrieve results from file        
        with open(finished_task["output_file"], "rb") as fp:
            results = fp.read()
        
        return Result(
            result_id=finished_task["result_id"], 
            logs=log, 
            data=results,
            status_code=status_code
        )

    def __refresh_container_statuses(self):
        """ Refreshes the states of the containers.
        """
        for task in self.active_tasks:
            task["container"].reload()
        
    def __make_task_dir(self, result_id: int):
        """ Creates a task directory for a specific result.

            :param result_id: unique result id for which the folder is
                intended
        """
        
        task_dir = os.path.join(
            self.__tasks_dir, "task-{0:09d}".format(result_id)
        )
        self.log.info(f"Using '{task_dir}' for task")
        
        if os.path.exists(task_dir):
            self.log.debug(f"Task directory already exists: '{task_dir}'")
        else:
            try:
                os.makedirs(task_dir)
            except Exception as e:
                self.log.error(f"Could not create task directory: {task_dir}")
                self.log.exception(e)
                raise e

        return task_dir