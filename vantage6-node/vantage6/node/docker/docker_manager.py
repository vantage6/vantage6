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
import shutil

from typing import Dict, List, NamedTuple
from docker.models.containers import Container
from pathlib import Path

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


class DockerTask(object):
    log = logging.getLogger(logger_name(__name__))

    def __init__(self, image: str, vpn_manager: VPNManager, node_name: str,
                 result_id: int, tasks_dir: Path,
                 isolated_network_mgr: IsolatedNetworkManager,
                 database_uri: str, database_is_file: bool):
        # TODO make vars private
        self.image = image
        self.vpn_manager = vpn_manager
        self.node_name = node_name
        self.result_id = result_id
        self.__tasks_dir = tasks_dir
        self.isolated_network_mgr = isolated_network_mgr
        self.database_uri = database_uri
        self.database_is_file = database_is_file

        self.docker = docker.from_env()
        self.container = None
        self.status_code = None

        self.labels = {
            f"{APPNAME}-type": "algorithm",
            "node": self.node_name,
            "result_id": str(result_id)
        }
        self.helper_labels = self.labels
        self.helper_labels[f"{APPNAME}-type"] = "algorithm-helper"

        # FIXME: these values should be retrieved from DockerNodeContext
        #   in some way.
        self.tmp_folder = "/mnt/tmp"
        self.data_folder = "/mnt/data"

    def is_finished(self):
        """ Return True if algorithm container is finished """
        self.container.reload()
        return self.container.status == 'exited'

    def report_status(self):
        logs = self.container.logs().decode('utf8')

        # report if the container has a different status than 0
        self.status_code = self.container.attrs["State"]["ExitCode"]
        if self.status_code:
            self.log.error(f"Received non-zero exitcode: {self.status_code}")
            self.log.error(f"  Container id: {self.container.id}")
            self.log.warn("Will not remove container")
            self.log.info(logs)
        return logs

    def get_results(self):
        with open(self.output_file, "rb") as fp:
            results = fp.read()
        return results

    def pull(self):
        """Pull the latest image."""
        try:
            self.log.info(f"Retrieving latest image: '{self.image}'")
            pull_if_newer(self.docker, self.image, self.log)

        except Exception as e:
            self.log.debug('Failed to pull image')
            self.log.error(e)

    def run_algorithm(self):
        vpn_port = None
        if self.vpn_manager.has_vpn:
            # if VPN is active, network exceptions must be configured
            # First, start a container that runs indefinitely. The algorithm
            # container will run in the same network and network exceptions
            # will therefore also affect the algorithm.
            self.helper_container = self.docker.containers.run(
                command='sleep infinity',
                image='alpine',
                labels=self.helper_labels,
                network=self.isolated_network_mgr.network_name,
                detach=True
            )
            # setup forwarding of traffic via VPN client to and from the
            # algorithm container:
            vpn_port = self.vpn_manager.forward_vpn_traffic(
                algo_container=self.helper_container)

        # Try to pull the latest image
        self.pull()

        # attempt to run the image
        try:
            self.log.info(f"Run docker image={self.image}")
            self.container = self.docker.containers.run(
                self.image,
                detach=True,
                environment=self.environment_variables,
                network='container:' + self.helper_container.id,
                volumes=self.volumes,
                labels=self.labels
            )
        except Exception as e:
            self.log.error('Could not run docker image!?')
            self.log.error(e)
            return None

        return vpn_port

    def _make_task_folders(self):
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
        self.task_folder_name = f"task-{self.result_id:09d}"
        self.task_folder_path = \
            os.path.join(self.__tasks_dir, self.task_folder_name)
        os.makedirs(self.task_folder_path, exist_ok=True)
        self.output_file = os.path.join(self.task_folder_path, "output")

    def _prepare_volumes(self, docker_input, tmp_vol_name, token):
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
            filepath = os.path.join(self.task_folder_path, filename)

            with open(filepath, 'wb') as fp:
                fp.write(data)

        volumes = {
            tmp_vol_name: {"bind": self.tmp_folder, "mode": "rw"},
        }

        if running_in_docker():
            volumes[self.data_volume_name] = \
                {"bind": self.data_folder, "mode": "rw"}
        else:
            volumes[self.__tasks_dir] = \
                {"bind": self.data_folder, "mode": "rw"}
        return volumes

    def _setup_environment_vars(self, algorithm_env: Dict = {}):
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
            "INPUT_FILE": f"{self.data_folder}/{self.task_folder_name}/input",
            "OUTPUT_FILE":
                f"{self.data_folder}/{self.task_folder_name}/output",
            "TOKEN_FILE": f"{self.data_folder}/{self.task_folder_name}/token",
            "TEMPORARY_FOLDER": self.tmp_folder,
            "HOST": f"http://{proxy_host}",
            "PORT": os.environ.get("PROXY_SERVER_PORT", 8080),
            "API_PATH": "",
        }
        if self.database_is_file:
            environment_variables["DATABASE_URI"] = \
                f"{self.data_folder}/{self.database_uri}"
        else:
            environment_variables["DATABASE_URI"] = self.database_uri
        self.log.debug(f"environment: {environment_variables}")

        # Load additional environment variables
        if algorithm_env:
            environment_variables = \
                {**environment_variables, **algorithm_env}
            self.log.info('Custom environment variables are loaded!')
            self.log.debug(f"custom environment: {algorithm_env}")
        return environment_variables

    def run(self, docker_input: bytes, tmp_vol_name: int, token: str,
            algorithm_env: Dict) -> int:
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
        # generate task folders
        self._make_task_folders()

        # prepare volumes
        self.volumes = self._prepare_volumes(
            docker_input, tmp_vol_name, token
        )
        self.log.debug(f"volumes: {self.volumes}")

        # setup environment variables
        self.environment_variables = \
            self._setup_environment_vars(algorithm_env=algorithm_env)

        # run the algorithm as docker container
        vpn_port = self.run_algorithm()
        return vpn_port

    def cleanup(self):
        self._remove_container(self.helper_container, kill=True)
        if not self.status_code:
            self._remove_container(self.container)

    def _remove_container(self, container: Container, kill=False) -> None:
        """
        Removes a docker container

        Parameters
        ----------
        container: docker.models.containers.Container
            The container that should be removed
        kill: bool
            Whether or not container should be killed before it is removed
        """
        try:
            if kill:
                container.kill()
            container.remove()
        except Exception as e:
            self.log.error(f"Failed to remove container {container.name}")
            self.log.debug(e)


class DockerManager(object):
    """ Wrapper for the docker module, to be used specifically for vantage6.

        It handles docker images names to results `run(image)`. It manages
        docker images, files (input, output, token, logs). Docker images run
        in detached mode, which allows to run multiple docker containers at
        the same time. Results (async) can be retrieved through
        `get_result()` which returns the first available result.
    """
    log = logging.getLogger(logger_name(__name__))

    def __init__(self, ctx, config,
                 isolated_network_mgr: IsolatedNetworkManager,
                 vpn_manager: VPNManager) -> None:
        """ Initialization of DockerManager creates docker connection and
            sets some default values.

            :param allowed_repositories: allowed urls for docker-images.
                Empty list implies that all repositoies are allowed.
            :param tasks_dir: folder to store task related data.
        """
        self.log.debug("Initializing DockerManager")
        self.data_volume_name = ctx.docker_volume_name
        self.algorithm_env = config.get('algorithm_env', {})
        self.vpn_manager = vpn_manager

        # Connect to docker daemon
        self.docker = docker.from_env()

        # keep track of the running containers
        self.active_tasks: List[DockerTask] = []

        # before a task is executed it gets exposed to these regex
        self._allowed_images = config.get("allowed_images")

        # isolated network to which algorithm containers can attach
        self.isolated_network_mgr = isolated_network_mgr

        # node name is used to identify algorithm containers belonging
        # to this node. This is required as multiple nodes may run at
        # a single machine sharing the docker daemon while using a
        # different server. Using a different server means that there
        # could be duplicate result_id's running at the node at the same
        # time.
        self.node_name = ctx.name

        # login to the registries
        docker_registries = ctx.config.get("docker_registries", [])
        self.login_to_registries(docker_registries)

        # set (and possibly create) the task directories
        self._set_task_dir(ctx)

        # set database uri and whether or not it is a file
        self._set_database(config)

    def _set_task_dir(self, ctx):
        # If we're in a 'regular' context, we'll copy the dataset to our data
        # dir and mount it in any algorithm container that's run; bind mounts
        # on a folder will work just fine.
        #
        # If we're running in dockerized mode we *cannot* bind mount a folder,
        # because the folder is in the container and not in the host. We'll
        # have to use a docker volume instead. This means:
        #  1. we need to know the name of the volume so we can pass it along
        #  2. need to have this volume mounted so we can copy files to it.
        #
        #  Ad 1: We'll use a default name that can be overridden by an
        #        environment variable.
        #  Ad 2: We'll expect `ctx.data_dir` to point to the right place. This
        #        is OK, since ctx will be a DockerNodeContext.
        #
        #  This also means that the volume will have to be created & mounted
        #  *before* this node is started, so we won't do anything with it here.

        # We'll create a subfolder in the data_dir. We need this subfolder so
        # we can easily mount it in the algorithm containers; the root folder
        # may contain the private key, which which we don't want to share.
        # We'll only do this if we're running outside docker, otherwise we
        # would create '/data' on the data volume.
        if not ctx.running_in_docker:
            self.__tasks_dir = ctx.data_dir / 'data'
            os.makedirs(self.__tasks_dir, exist_ok=True)
        else:
            self.__tasks_dir = ctx.data_dir

    def _set_database(self, config):
        # If we're running in a docker container, database_uri would point
        # to a path on the *host* (since it's been read from the config
        # file). That's no good here. Therefore, we expect the CLI to set
        # the environment variable for us. This has the added bonus that we
        # can override the URI from the command line as well.
        default_uri = config['databases']['default']
        self.database_uri = os.environ.get('DATABASE_URI', default_uri)

        self.database_is_file = False
        if Path(self.database_uri).exists():
            # We'll copy the file to the folder `data` in our task_dir.
            self.log.info(f'Copying {self.database_uri} to {self.__tasks_dir}')
            shutil.copy(self.database_uri, self.__tasks_dir)

            # Since we've copied the database to the folder 'data' in the root
            # of the volume: '/data/<database.csv>'. We'll just keep the
            # basename (i.e. filename + ext).
            self.database_uri = os.path.basename(self.database_uri)
            self.database_is_file = True

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

        task = DockerTask(
            image=image,
            result_id=result_id,
            vpn_manager=self.vpn_manager,
            node_name=self.node_name,
            tasks_dir=self.__tasks_dir,
            isolated_network_mgr=self.isolated_network_mgr,
            database_uri=self.database_uri,
            database_is_file=self.database_is_file
        )
        vpn_port = task.run(
            docker_input=docker_input, tmp_vol_name=tmp_vol_name, token=token,
            algorithm_env=self.algorithm_env
        )

        # keep track of the active container
        self.active_tasks.append(task)

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
            finished_tasks = [t for t in self.active_tasks if t.is_finished()]
            time.sleep(1)

        # at least one task is finished
        finished_task = finished_tasks.pop()
        self.log.debug(f"Result id={finished_task.result_id} is finished")

        # Check exit status and report
        logs = finished_task.report_status()

        # Cleanup containers
        finished_task.cleanup()

        # Retrieve results from file
        results = finished_task.get_results()

        # remove finished tasks from active task list
        self.active_tasks.remove(finished_task)

        return Result(
            result_id=finished_task.result_id,
            logs=logs,
            data=results,
            status_code=finished_task.status_code
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
