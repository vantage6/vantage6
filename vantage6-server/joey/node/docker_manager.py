import time
import logging
import docker
import os
import pathlib

from typing import NamedTuple

import joey.constants as cs

class Result(NamedTuple):
    """Data class to store the result of the docker image."""
    result_id: int
    logs: str
    data: str
    status_code: int

class DockerManager(object):
    """Wrapper for the docker module, to be used specifically for joey.
    
    It handles docker images names to results `run(image)`. It manages 
    docker images, files (input, output, token, logs). Docker images run 
    in detached mode, which allows to run multiple docker containers at 
    the same time. Results (async) can be retrieved through 
    `get_result()` which returns the first available result.
    """

    log = logging.getLogger(__name__.split('.')[-1])
    
    # TODO validate that allowed repositoy is used
    # TODO authenticate to docker repository... from the config-file

    def __init__(self, allowed_repositories, tasks_dir, 
        isolated_network_name: str) -> None:
        """Initialization of DockerManager creates docker connection and
        sets some default values.
        
        :param allowed_repositories: allowed urls for docker-images. 
            Empty list implies that all repositoies are allowed.
        :param tasks_dir: folder to store task related data.
        """
        self.log.debug("Initializing DockerManager")
        self.__tasks_dir = tasks_dir
        # TODO this is no longer needed, as the local proxy server 
        # handles this.
        # master container need to know where they can post tasks to
        # self.__server_info = server_info

        self.client = docker.from_env()

        # keep track of the running containers
        self.active_tasks = []

        # TODO this still needs to be checked
        self.__allowed_repositories = allowed_repositories
        
        # create / get isolated network to which algorithm containers 
        # can attach
        self.isolated_network = \
            self.create_isolated_network(isolated_network_name)
    
    def create_isolated_network(self, name: str) \
        -> docker.models.networks.Network:
        """Create an internal network 
        
        Used by algorithm containers to communicate with the node API.

        :param name: name of the internal network
        """
        try:
            network = self.client.networks.get(name)
            self.log.debug(f"Network {name} already exists.")
        except:
            self.log.debug(f"Creating docker-network {name}")
            network = self.client.networks.create(
                name, 
                driver="bridge",
                internal=True,
                scope="local"
            )

        return network

    def create_bind(self, filename: str, result_id: int, filecontents) \
        -> docker.types.services.Mount:
        input_path = self.__create_file_on_host(filename, result_id, filecontents)

        return docker.types.Mount(
            f"/app/{filename}", 
            input_path, 
            type="bind"
        )
    
    def create_temporary_volume(self, run_id:int):
        volume_name = f"tmp_{run_id}"
        try:
            self.client.volumes.get(volume_name)
            self.log.debug(f"Volume {volume_name} already exists.")
        except docker.errors.NotFound:
            self.log.debug(f"Creating volume {volume_name}")
            self.client.volumes.create(volume_name)

    def run(self, result_id: int,  image: str, database_uri: str, 
                docker_input: str, run_id: int, token: str) -> bool:
        """Runs the docker-image in detached mode.
        
        :param result_id: server result identifyer.
        :param image: docker image name.
        :param docker_input: input that can be read by docker container.
        :param token: Bearer token that the container can use.
        """

        # create I/O files for docker
        mounts = []
        mount_files = [
            ('input', docker_input), 
            ('output', ''), 
            ('token', token), 
        ]
        files = {}
        for (filename, contents) in mount_files:
            input_path, host_input_path = self.__create_file_on_host(filename+".txt", result_id, 
                contents)
            mounts.append(docker.types.Mount(
                f"/app/{filename}.txt", 
                host_input_path,
                type="bind"
            ))
            files[filename+"_file"] = input_path

        # If the provided database URI is a file, we need to mount
        # it at a predefined path and update the environment variable
        # that's passed to the container.
        if database_uri:
            if pathlib.Path(database_uri).is_file():
                mounts.append(
                    docker.types.Mount(
                        "/app/database", 
                        database_uri, 
                        type="bind"
                    )
                )
                database_uri = "/app/database"

            else:
                self.log.warning("'{}' is not a file!".format(database_uri))
        else:
            self.log.warning('no database specified')

        # attempt to pull the latest image
        try:
            self.log.info(f"Retrieving latest image={image}")
            self.client.images.pull(image)
        except Exception as e:
            self.log.error(e)
        
        # define enviroment variables for the docker-container, the 
        # host, port and api_path are from the local proxy server to 
        # facilitate indirect communication with the central server
        environment_variables = {
            "DATABASE_URI": database_uri,
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
                mounts=mounts,
                environment=environment_variables,
                network=self.isolated_network.name,
                volumes={
                    f"tmp_{run_id}":{
                        "bind":"/mnt/tmp",
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
            "output_file": files["output_file"]
        })

        return True

    def get_result(self):
        """Returns the oldest (FIFO) finished docker container.
        
        This is a blocking method until a finished container shows up.
        Once the container is obtained and the results are red, the 
        container is removed from the docker environment."""

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
        with open(finished_task["output_file"]) as fp:
            results = fp.read()
        
        return Result(
            result_id=finished_task["result_id"], 
            logs=log, 
            data=results,
            status_code=status_code
        )

    def __refresh_container_statuses(self):
        """Refreshes the states of the containers."""
        for task in self.active_tasks:
            task["container"].reload()
        
    def __create_file_on_host(self, filename: str, result_id: int, content: str):
        """Creates a file in the tasks_dir for a specific task."""
        
        # generate file paths
        task_dir = self.__make_task_dir(result_id)
        path = os.path.join(task_dir, filename)
        
        # create files
        with open(path, 'w') as fp:
            fp.write(content + "\n")

        # convert to host path
        # TODO windows only solution!
        host_input_path = path.replace("/mnt/data", os.environ["HOST_DATA_DIR"])
        host_input_path = host_input_path.replace("C:","/c")
        host_input_path = host_input_path.replace("\\","/")

        return path, host_input_path

    def __make_task_dir(self, result_id: int):
        """Creates a task directory for a specific result."""
        
        task_dir = os.path.join(
            self.__tasks_dir, "task-{0:09d}".format(result_id))
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