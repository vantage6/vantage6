import time
import logging
import docker
import os
import pathlib


from typing import NamedTuple

class Result(NamedTuple):
    """Data class to store the result of the docker image."""
    result_id: int
    logs: str
    data: str

class DockerManager(object):
    """Wrapper for the docker module, to be used specifically for ppDLI.
    
    It handles docker images names to results `run(image)`. It manages 
    docker images, files (input, output, token, logs). Docker images run 
    in detached mode, which allows to run multiple docker containers at 
    the same time. Results (async) can be retrieved through 
    `get_result()` which returns the first available result.
    """

    log = logging.getLogger(__name__.split('.')[-1])
    
    # TODO validate that allowed repositoy is used
    # TODO authenticate to docker repository... from the config-file

    def __init__(self, allowed_repositories, tasks_dir):
        """Initialization of DockerManager creates docker connection and
        sets some default values.
        
        :param allowed_repositories: allowed urls for docker-images. 
            Empty list implies that all repositoies are allowed.
        :param tasks_dir: folder to store task related data.
        """
        self.log.debug("Initializing DockerManager")
        self.client = docker.from_env()

        self.tasks = []

        self.__allowed_repositories = allowed_repositories
        self.__tasks_dir = tasks_dir
    
    def create_bind(self, filename, result_id, filecontents):
        input_path = self.__create_file(filename, result_id, filecontents)

        return docker.types.Mount(
            f"/app/{filename}", 
            input_path, 
            type="bind"
        )

    def run(self, result_id: int,  image: str, database_uri: str, 
                docker_input: str, token: str):
        """Runs the docker-image in detached mode.
        
        :param result_id: server result identifyer.
        :param image: docker image name.
        :param docker_input: input that can be read by docker container.
        :param token: Bearer token that the container can use.
        """
        
        # create I/O files for docker
        mounts = []

        """
            # files = [
            #     ('input.txt', docker_input), 
            #     ('output.txt', ''), 
            #     ('token.txt', token), 
            # ]

            # for (filename, contents) in files:
            #     bind = self.create_bind(filename, result_id, contents)
            #     mounts.append(bind)
        """

        input_path = self.__create_file("input.txt", result_id, docker_input)
        self.log.info(f'input_path: {input_path}')
        mounts.append(
            docker.types.Mount(
                "/app/input.txt", 
                input_path,
                type="bind"
            )
        )

        output_path = self.__create_file("output.txt", result_id, "")
        self.log.info(f'output_path: {output_path}')
        mounts.append(
            docker.types.Mount(
                "/app/output.txt", 
                output_path, 
                type="bind"
            )
        )
    
        token_path = self.__create_file("token.txt", result_id, token)
        self.log.info(f'token_path: {token_path}')
        mounts.append(
            docker.types.Mount(
                "/app/token.txt", 
                token_path, 
                type="bind"
            )
        )

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
        
        # attempt to run the image
        try:
            self.log.info(f"Run docker image={image}")
            container = self.client.containers.run(
                image, 
                detach=True, 
                mounts=mounts,
                environment={'DATABASE_URI': database_uri}
            )
        except Exception as e:
            self.log.debug(e)
            return False

        # keep track of the container
        self.tasks.append({
            "result_id": result_id,
            "container": container,
            "output_file": output_path
        })

        return True

    def get_result(self):
        """Returns the oldest (FIFO) finished docker container.
        
        This is a blocking method until a finished container shows up.
        Once the container is obtained and the results are red, the 
        container is removed from the docker environment."""

        # get finished results and get the first one, if no result is available this is blocking
        while True:
            self.__refresh_container_statuses()
            try:
                # FIXME: Use list comprehension instead? e.g.
                #   finished_tasks = [t for t in self.tasks if t['container'].status == 'exited']
                finished_task = next(
                    filter(
                        lambda task: task["container"].status == "exited", 
                        self.tasks
                    )
                )
                self.log.debug(
                    f"Result id={finished_task['result_id']} is finished"
                )
                break

            except StopIteration:
                # FIXME: without sleeping, this will burn CPU cycles!
                time.sleep(1)
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
        
        return Result(
            result_id=finished_task["result_id"], 
            logs=log, 
            data=results
        )

    def __refresh_container_statuses(self):
        """Refreshes the states of the containers."""
        for task in self.tasks:
            task["container"].reload()
        
    def __create_file(self, filename: str, result_id: int, content: str):
        """Creates a file in the tasks_dir for a specific task."""
        
        # generate file paths
        task_dir = self.__make_task_dir(result_id)
        path = os.path.join(task_dir, filename)
        
        # create files
        with open(path, 'w') as fp:
            fp.write(content + "\n")

        return path

    def __make_task_dir(self, result_id: int):
        """Creates a task directory for a specific result."""
        
        task_dir = os.path.join(self.__tasks_dir, "task-{0:09d}".format(result_id))
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