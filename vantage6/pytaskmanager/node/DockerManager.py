import logging
import docker
import os

from typing import NamedTuple

class Result(NamedTuple):
    """Data class to return the docker results."""
    result_id: int
    logs: str
    data: str

class DockerDirs(NamedTuple):
    result_id: int
    input_dir: str
    output_dir: str


class DockerManager(object):
    """Wrapper for the docker module, to be used specifically for ppDLI.
    
    It handles docker images names to results `run(image)`. It manages docker images, 
    files (input, output, logs). Docker images run in detached mode, which allows
    to run multiple docker containers at the same time. Results (async) can be retrieved 
    through `get_result()` which returns the first available result.
    """

    log = logging.getLogger(__name__.split('.')[-1])
    
    # TODO validate that allowed repositoy is used
    # TODO authenticate to docker repository... from the config-file

    def __init__(self, allowed_repositories=[], tasks_dir=None):
        """Setups the docker service.
        
        :param allowed_repositories: allowed urls for docker-images. Empty list
            means all repositoies are allowed.
        :returns: None
        """

        self.log.debug("Initializing DockerManager")
        self.client = docker.from_env()

        self.tasks = []

        self.__allowed_repositories = allowed_repositories
        self.__tasks_dir = tasks_dir
        
    def run(self, result_id: int,  image: str="hello-world", docker_input: str=""):
        """Runs the docker-image in detached mode."""
        
        # create I/O files for docker
        input_file, output_file = self.__prepare_IO_files(result_id, docker_input)
        input_mount = docker.types.Mount("/app/input.txt", input_file.replace(' ', '\ '), type="bind")
        output_mount = docker.types.Mount("/app/output.txt", output_file.replace(' ', '\ '), type="bind")

        # attempt to pull the latest image
        try:
            self.log.info(f"Retrieving latest image={image}")
            self.client.images.pull(image)
        except Exception as e:
            self.log.error(e)
        
        # attempt to run the image
        try:
            self.log.info(f"Run docker image={image}")
            container = self.client.containers.run(
                image, 
                detach=True, 
                mounts=[input_mount, output_mount]
            )
        except Exception as e:
            self.log.debug(e)
            return False

        # keep track of the containers
        self.tasks.append({
            "result_id": result_id,
            "container": container,
            "output_file": output_file
        })

        return True

    def get_result(self):
        """Returns the oldest finished docker container and removes it from the manager.
        If no result is available this function is blocking untill one comes available."""

        # get finished results and get the first one, if no result is available this is blocking
        while True:
            self.__refresh_container_statuses()
            try:
                finished_task = next(filter(lambda task: task["container"].status == "exited", self.tasks))
                self.log.debug(f"Result id={finished_task['result_id']} is finished")
                break
            except StopIteration:
                continue
        
        # get all info from the container and cleanup
        container = finished_task["container"]
        log = container.logs().decode('utf8')
        try:
            container.remove()
        except Exception as e:
            self.log.error(f"Failed to remove container {container}")
            self.log.debug(e)
        self.tasks.remove(finished_task)
        
        # retrieve results from file        
        with open(finished_task["output_file"]) as fp:
            results = fp.read()
        
        return Result(result_id=finished_task["result_id"], logs=log, data=results)

    def __refresh_container_statuses(self):
        for task in self.tasks:
            task["container"].reload()
        # map(lambda task: task["container"].reload(), self.tasks)

    def __prepare_IO_files(self, result_id: int, docker_input: str):
        """Creates input.txt (containing docker_input) and output.txt."""
        
        # generate file paths
        task_dir = self.__make_task_dir(result_id)
        input_file = os.path.join(task_dir, "input.txt")
        output_file = os.path.join(task_dir, "output.txt")

        # create files
        with open(input_file, 'w') as fp:
            fp.write(docker_input + "\n")
        with open(output_file, 'w') as fp:
            fp.write("")

        return input_file, output_file

    def __make_task_dir(self, result_id: int):
        
        task_dir = os.path.join(self.__tasks_dir, "task-{0:09d}".format(result_id))
        self.log.info(f"Using '{task_dir}' for task")
        
        if os.path.exists(task_dir):
            self.log.warning(f"Task directory already exists: '{task_dir}'")
        else:
            try:
                os.makedirs(task_dir)
            except Exception as e:
                self.log.error(f"Could not create task directory: {task_dir}")
                self.log.exception(e)
                raise e

        return task_dir