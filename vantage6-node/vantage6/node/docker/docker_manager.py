""" Docker manager

The docker manager is responsible for communicating with the docker-
daemon and is a wrapper arround the docker module. It has methods
for creating docker networks, docker volumes, start containers
and retreive results from finished containers

TODO the task folder is also created by this class. This folder needs
to be cleaned at some point.
"""
import os
import time
import logging
import docker
import re

from typing import NamedTuple

from vantage6.common.docker_addons import pull_if_newer
from vantage6.common.globals import APPNAME
from vantage6.node.docker.vpn_manager import VPNManager
from vantage6.node.util import logger_name
from vantage6.node.docker.network_manager import IsolatedNetworkManager
from vantage6.node.docker.utils import running_in_docker

log = logging.getLogger(logger_name(__name__))


class Result(NamedTuple):
    """ Data class to store the result of the docker image."""
    result_id: int
    logs: str
    data: str
    status_code: int


class DockerManager(object):
    """ Wrapper for the docker module, to be used specifically for vantage6.

        It handles docker images names to results `run(image)`. It manages
        docker images, files (input, output, token, logs). Docker images run
        in detached mode, which allows to run multiple docker containers at
        the same time. Results (async) can be retrieved through
        `get_result()` which returns the first available result.
    """
    log = logging.getLogger(logger_name(__name__))

    def __init__(self, allowed_images, tasks_dir,
                 isolated_network_mgr: IsolatedNetworkManager,
                 node_name: str, data_volume_name: str,
                 docker_registries: list, vpn_manager: VPNManager) -> None:
        """ Initialization of DockerManager creates docker connection and
            sets some default values.

            :param allowed_repositories: allowed urls for docker-images.
                Empty list implies that all repositoies are allowed.
            :param tasks_dir: folder to store task related data.
        """
        self.log.debug("Initializing DockerManager")
        self.data_volume_name = data_volume_name
        self.database_uri = None
        self.database_is_file = False
        self.__tasks_dir = tasks_dir
        self.algorithm_env = {}
        self.vpn_manager = vpn_manager

        # Connect to docker daemon
        self.docker = docker.from_env()

        # keep track of the running containers
        self.active_tasks = []

        # before a task is executed it gets exposed to these regex
        self._allowed_images = allowed_images

        # isolated network to which algorithm containers can attach
        self.isolated_network_mgr = isolated_network_mgr

        # node name is used to identify algorithm containers belonging
        # to this node. This is required as multiple nodes may run at
        # a single machine sharing the docker daemon while using a
        # different server. Using a different server means that there
        # could be duplicate result_id's running at the node at the same
        # time.
        self.node_name = node_name

        # TODO self.vpn_client_container_name

        # login to the registries
        self.login_to_registries(docker_registries)

    def __refresh_container_statuses(self):
        """ Refreshes the states of the containers.
        """
        for task in self.active_tasks:
            task["container"].reload()

    def create_volume(self, volume_name: str):
        """Create a temporary volume for a single run.

            A single run can consist of multiple algorithm containers.
            It is important to note that all algorithm containers having
            the same run_id have access to this container.

            :param run_id: integer representing the run_id
        """
        try:
            self.docker.volumes.get(volume_name)
            self.log.debug(f"Volume {volume_name} already exists.")

        except docker.errors.NotFound:
            self.log.debug(f"Creating volume {volume_name}")
            self.docker.volumes.create(volume_name)

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

    def is_running(self, result_id):
        """Return True if a container is already running for <result_id>."""
        running_containers = self.docker.containers.list(filters={
            "label": [
                f"{APPNAME}-type=algorithm",
                f"node={self.node_name}",
                f"result_id={result_id}"
            ]
        })
        return bool(running_containers)

    def pull(self, image):
        """Pull the latest image."""
        try:
            self.log.info(f"Retrieving latest image: '{image}'")
            pull_if_newer(self.docker, image, self.log)

        except Exception as e:
            self.log.debug('Failed to pull image')
            self.log.error(e)

    def set_database_uri(self, database_uri):
        """A setter for clarity."""
        self.database_uri = database_uri

    def run_algorithm(self, image, environment_variables, volumes, result_id,
                      task_folder):
        labels = {
            "node": self.node_name,
            "result_id": str(result_id)
        }

        vpn_port = None
        if self.vpn_manager.has_vpn:
            # if VPN is active, network exceptions must be configured
            # First, start a container that runs indefinitely. The algorithm
            # container will run in the same network and network exceptions
            # will therefore also affect the algorithm.
            # TODO TODO When algorithm finishes, also clean up this container
            helper_labels = labels
            helper_labels[f"{APPNAME}-type"] = "algorithm-helper"
            config_container = self.docker.containers.run(
                command='sleep infinity',
                image='alpine',
                labels=helper_labels,
                network=self.isolated_network_mgr.network_name,
                detach=True
            )
            # setup forwarding of traffic via VPN client to and from the
            # algorithm container:
            vpn_port = self.vpn_manager.forward_vpn_traffic(
                algo_container=config_container)

        # Try to pull the latest image
        self.pull(image)

        # attempt to run the image
        try:
            self.log.info(f"Run docker image={image}")
            algo_labels = labels
            algo_labels[f"{APPNAME}-type"] = "algorithm"
            container = self.docker.containers.run(
                image,
                detach=True,
                environment=environment_variables,
                network='container:' + config_container.id,
                volumes=volumes,
                labels=algo_labels
            )
        except Exception as e:
            self.log.error('Could not run docker image!?')
            self.log.error(e)
            return None

        # keep track of the container
        self.active_tasks.append({
            "result_id": result_id,
            "container": container,
            "output_file": os.path.join(task_folder, "output")
        })

        return vpn_port

    def _make_task_folders(self, result_id):
        # FIXME: We should have a separate mount/volume for this. At the
        #   moment this is a potential leak as containers might access input,
        #   output and token from other containers.
        #
        #   This was not possible yet as mounting volumes from containers
        #   is terrible when working from windows (as you have to convert
        #   from windows to unix several times...).

        # If we're running in docker __tasks_dir will point to a location on
        # the data volume.
        # Alternatively, if we're not running in docker it should point to the
        # folder on the host that can act like a data volume. In both cases,
        # we can just copy the required files to it
        task_folder_name = f"task-{result_id:09d}"
        task_folder_path = os.path.join(self.__tasks_dir, task_folder_name)
        os.makedirs(task_folder_path, exist_ok=True)
        return task_folder_name, task_folder_path

    def _prepare_volumes(
            self, docker_input, task_folder_path, tmp_vol_name, token):
        if isinstance(docker_input, str):
            docker_input = docker_input.encode('utf8')

        # Create I/O files & token for the algorithm container
        self.log.debug("prepare IO files in docker volume")
        io_files = [
            ('input', docker_input),
            ('output', b''),
            ('token', token.encode("ascii")),
        ]

        for (filename, data) in io_files:
            filepath = os.path.join(task_folder_path, filename)

            with open(filepath, 'wb') as fp:
                fp.write(data)

        # FIXME: these values should be retrieved from DockerNodeContext
        #   in some way. TODO TODO TODO
        tmp_folder = "/mnt/tmp"
        data_folder = "/mnt/data"

        volumes = {
            tmp_vol_name: {"bind": tmp_folder, "mode": "rw"},
        }

        if running_in_docker():
            volumes[self.data_volume_name] = \
                {"bind": data_folder, "mode": "rw"}

        else:
            volumes[self.__tasks_dir] = {"bind": data_folder, "mode": "rw"}
        return volumes, data_folder, tmp_folder

    def _setup_environment_vars(
            self, data_folder, task_folder_name, tmp_folder):
        try:
            proxy_host = os.environ['PROXY_SERVER_HOST']

        except Exception:
            print('-' * 80)
            print(os.environ)
            print('-' * 80)
            proxy_host = 'host.docker.internal'

        # define enviroment variables for the docker-container, the
        # host, port and api_path are from the local proxy server to
        # facilitate indirect communication with the central server
        # FIXME: we should only prepend data_folder if database_uri is a
        #   filename
        environment_variables = {
            "INPUT_FILE": f"{data_folder}/{task_folder_name}/input",
            "OUTPUT_FILE": f"{data_folder}/{task_folder_name}/output",
            "TOKEN_FILE": f"{data_folder}/{task_folder_name}/token",
            "TEMPORARY_FOLDER": tmp_folder,
            "HOST": f"http://{proxy_host}",
            "PORT": os.environ.get("PROXY_SERVER_PORT", 8080),
            "API_PATH": "",
        }
        if self.database_is_file:
            environment_variables["DATABASE_URI"] = \
                f"{data_folder}/{self.database_uri}"
        else:
            environment_variables["DATABASE_URI"] = self.database_uri
        self.log.debug(f"environment: {environment_variables}")

        # Load additional environment variables
        if self.algorithm_env:
            environment_variables = \
                {**environment_variables, **self.algorithm_env}
            self.log.info('Custom environment variables are loaded!')
            self.log.debug(f"custom environment: {self.algorithm_env}")
        return environment_variables

    def run(self, result_id: int,  image: str, docker_input: bytes,
            tmp_vol_name: int, token: str) -> int:
        """Runs the docker-image in detached mode.

            It will will attach all mounts (input, output and datafile)
            to the docker image. And will supply some environment
            variables.

            :param result_id: server result identifier
            :param image: docker image name
            :param docker_input: input that can be read by docker container
            :param run_id: identifieer of the run sequence
            :param token: Bearer token that the container can use
        """
        # Verify that an allowed image is used
        if not self.is_docker_image_allowed(image):
            msg = f"Docker image {image} is not allowed on this Node!"
            self.log.critical(msg)
            return None

        # Check that this task is not already running
        if self.is_running(result_id):
            self.log.warn("Task is already being executed, discarding task")
            self.log.debug(f"result_id={result_id} is discarded")
            return None

        # generate task folders
        task_folder_name, task_folder_path = self._make_task_folders(result_id)

        # prepare volumes
        volumes, data_folder, tmp_folder = self._prepare_volumes(
            docker_input, task_folder_path, tmp_vol_name, token
        )
        self.log.debug(f"volumes: {volumes}")

        # setup environment variables
        environment_variables = self._setup_environment_vars(
            data_folder, task_folder_name, tmp_folder
        )

        # run the algorithm as docker container
        vpn_port = self.run_algorithm(
            image, environment_variables, volumes, result_id, task_folder_path
        )

        return vpn_port

    def get_result(self):
        """
        Returns the oldest (FIFO) finished docker container.

        This is a blocking method until a finished container shows up. Once the
        container is obtained and the results are read, the container is
        removed from the docker environment.

        Returns
        -------
        Result
            result of the docker image
        """

        # get finished results and get the first one, if no result is available
        # this is blocking
        finished_tasks = []

        while not finished_tasks:
            self.__refresh_container_statuses()

            finished_tasks = [t for t in self.active_tasks
                              if t['container'].status == 'exited']

            time.sleep(1)

        # at least one task is finished
        finished_task = finished_tasks.pop()

        self.log.debug(
            f"Result id={finished_task['result_id']} is finished"
        )

        # get all info from the container and cleanup
        container = finished_task["container"]
        log = container.logs().decode('utf8')

        # report if the container has a different status than 0
        status_code = container.attrs["State"]["ExitCode"]

        if status_code:
            self.log.error(f"Received non-zero exitcode: {status_code}")
            self.log.error(f"  Container id: {container.id}")
            self.log.warn("Will not remove container")
            self.log.info(log)

        else:
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

    def login_to_registries(self, registies: list = []) -> None:

        for registry in registies:
            try:
                self.docker.login(
                    username=registry.get("username"),
                    password=registry.get("password"),
                    registry=registry.get("registry")
                )
                self.log.info(f"Logged in to {registry.get('registry')}")
            except docker.errors.APIError as e:
                self.log.warn(f"Could not login to {registry.get('registry')}")
                self.log.debug(e)
