"""
Docker manager

The docker manager is responsible for communicating with the docker-daemon and
is a wrapper around the docker module. It has methods
for creating docker networks, docker volumes, start containers and retrieve
results from finished containers.
"""

import os
import time
import logging
import docker
import re
import shutil

from typing import NamedTuple
from pathlib import Path

from vantage6.common import logger_name
from vantage6.common import get_database_config
from vantage6.common.docker.addons import (
    get_container,
    running_in_docker,
)
from vantage6.common.globals import APPNAME, BASIC_PROCESSING_IMAGE
from vantage6.common.task_status import TaskStatus, has_task_failed
from vantage6.common.docker.network_manager import NetworkManager
from vantage6.algorithm.tools.wrappers import get_column_names
from vantage6.cli.context.node import NodeContext
from vantage6.node.context import DockerNodeContext
from vantage6.node.docker.docker_base import DockerBaseManager
from vantage6.node.docker.vpn_manager import VPNManager
from vantage6.node.docker.task_manager import DockerTaskManager
from vantage6.node.docker.squid import Squid
from vantage6.common.client.node_client import NodeClient
from vantage6.node.docker.exceptions import (
    UnknownAlgorithmStartFail,
    PermanentAlgorithmStartFail,
    AlgorithmContainerNotFound,
)

log = logging.getLogger(logger_name(__name__))


class Result(NamedTuple):
    """
    Data class to store the result of the docker image.

    Attributes
    ----------
    run_id: int
        ID of the current algorithm run
    logs: str
        Logs attached to current algorithm run
    data: str
        Output data of the algorithm
    status_code: int
        Status code of the algorithm run
    """

    run_id: int
    task_id: int
    logs: str
    data: str
    status: str
    parent_id: int | None


class ToBeKilled(NamedTuple):
    """Data class to store which tasks should be killed"""

    task_id: int
    run_id: int
    organization_id: int


class KilledRun(NamedTuple):
    """Data class to store which algorithms have been killed"""

    run_id: int
    task_id: int
    parent_id: int


class DockerManager(DockerBaseManager):
    """
    Wrapper for the docker-py module.

    This class manages tasks related to Docker, such as logging in to
    docker registries, managing input/output files, logs etc. Results
    can be retrieved through `get_result()` which returns the first available
    algorithm result.
    """

    log = logging.getLogger(logger_name(__name__))

    def __init__(
        self,
        ctx: DockerNodeContext | NodeContext,
        isolated_network_mgr: NetworkManager,
        vpn_manager: VPNManager,
        tasks_dir: Path,
        client: NodeClient,
        proxy: Squid | None = None,
    ) -> None:
        """Initialization of DockerManager creates docker connection and
        sets some default values.

        Parameters
        ----------
        ctx: DockerNodeContext | NodeContext
            Context object from which some settings are obtained
        isolated_network_mgr: NetworkManager
            Manager for the isolated network
        vpn_manager: VPNManager
            VPN Manager object
        tasks_dir: Path
            Directory in which this task's data are stored
        client: NodeClient
            Client object to communicate with the server
        proxy: Squid | None
            Squid proxy object
        """
        self.log.debug("Initializing DockerManager")
        super().__init__(isolated_network_mgr)

        self.data_volume_name = ctx.docker_volume_name
        self.ctx = ctx
        config = ctx.config
        self.algorithm_env = config.get("algorithm_env", {})
        self.vpn_manager = vpn_manager
        self.client = client
        self.__tasks_dir = tasks_dir
        self.alpine_image = config.get("alpine")
        self.proxy = proxy

        # keep track of the running containers
        self.active_tasks: list[DockerTaskManager] = []

        # keep track of the containers that have failed to start
        self.failed_tasks: list[DockerTaskManager] = []

        # before a task is executed it gets exposed to these policies
        self._policies = self._setup_policies(config)

        # node name is used to identify algorithm containers belonging
        # to this node. This is required as multiple nodes may run at
        # a single machine sharing the docker daemon while using a
        # different server. Using a different server means that there
        # could be duplicate result_id's running at the node at the same
        # time.
        self.node_name = ctx.name

        # name of the container that is running the node
        self.node_container_name = ctx.docker_container_name

        # login to the registries
        docker_registries = ctx.config.get("docker_registries", [])
        self.login_to_registries(docker_registries)

        # set database uri and whether or not it is a file
        self._set_database(ctx.databases)

        # keep track of linked docker services
        self.linked_services: list[str] = []

        # set algorithm device requests
        self.algorithm_device_requests = []
        if "algorithm_device_requests" in config:
            self._set_algorithm_device_requests(config["algorithm_device_requests"])

    def _set_database(self, databases: dict | list) -> None:
        """
        Set database location and whether or not it is a file

        Parameters
        ----------
        databases: dict | list
            databases as specified in the config file
        """
        db_labels = [db["label"] for db in databases]

        # If we're running in a docker container, database_uri would point
        # to a path on the *host* (since it's been read from the config
        # file). That's no good here. Therefore, we expect the CLI to set
        # the environment variables for us. This has the added bonus that we
        # can override the URI from the command line as well.
        self.databases = {}
        for label in db_labels:
            label_upper = label.upper()
            db_config = get_database_config(databases, label)
            if running_in_docker():
                uri = os.environ[f"{label_upper}_DATABASE_URI"]
            else:
                uri = db_config["uri"]

            if running_in_docker():
                db_is_file = Path(f"/mnt/{uri}").exists()
                if db_is_file:
                    uri = f"/mnt/{uri}"
            else:
                db_is_file = Path(uri).exists()

            if db_is_file:
                # We'll copy the file to the folder `data` in our task_dir.
                self.log.info(f"Copying {uri} to {self.__tasks_dir}")
                shutil.copy(uri, self.__tasks_dir)
                uri = self.__tasks_dir / os.path.basename(uri)

            self.databases[label] = {
                "uri": uri,
                "is_file": db_is_file,
                "type": db_config["type"],
                "env": db_config.get("env", {}),
            }
        self.log.debug(f"Databases: {self.databases}")

    def _set_algorithm_device_requests(self, device_requests_config: dict) -> None:
        """
        Configure device access for the algorithm container.

        Parameters
        ----------
        device_requests_config: dict
           A dictionary containing configuration options for device access.
           Supported keys:
           - 'gpu': A boolean value indicating whether GPU access is required.
        """
        device_requests = []
        if device_requests_config.get("gpu", False):
            device = docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])
            device_requests.append(device)
        self.algorithm_device_requests = device_requests

    def _setup_policies(self, config: dict) -> dict:
        """
        Set up policies for the node.

        Parameters
        ----------
        config: dict
            Configuration dictionary

        Returns
        -------
        dict
            Dictionary with the policies
        """
        policies = config.get("policies", {})
        if not policies or not policies.get("allowed_algorithms"):
            self.log.warning(
                "No policies on allowed algorithms have been set for this node!"
            )
            self.log.warning(
                "This means that all algorithms are allowed to run on this node."
            )
        return policies

    def create_volume(self, volume_name: str) -> None:
        """
        Create a temporary volume for a single run.

        A single run can consist of multiple algorithm containers. It is
        important to note that all algorithm containers having the same job_id
        have access to this container.

        Parameters
        ----------
        volume_name: str
            Name of the volume to be created
        """
        try:
            self.docker.volumes.get(volume_name)
            self.log.debug(f"Volume {volume_name} already exists.")

        except docker.errors.NotFound:
            self.log.debug(f"Creating volume {volume_name}")
            self.docker.volumes.create(volume_name)

    def is_docker_image_allowed(self, docker_image_name: str, task_info: dict) -> bool:
        """
        Checks the docker image name.

        Against a list of regular expressions as defined in the configuration
        file. If no expressions are defined, all docker images are accepted.

        Parameters
        ----------
        docker_image_name: str
            uri to the docker image
        task_info: dict
            Dictionary with information about the task

        Returns
        -------
        bool
            Whether docker image is allowed or not
        """
        # check if algorithm matches any of the regex cases
        allow_basics = self._policies.get("allow_basics_algorithm", True)
        allowed_algorithms = self._policies.get("allowed_algorithms")
        if docker_image_name.startswith(BASIC_PROCESSING_IMAGE):
            if not allow_basics:
                self.log.warn(
                    "A task was sent with a basics algorithm that "
                    "this node does not allow to run."
                )
                return False
            # else: basics are allowed, so we don't need to check the regex
        elif allowed_algorithms:
            if isinstance(allowed_algorithms, str):
                allowed_algorithms = [allowed_algorithms]
            found = False
            for algorithm in allowed_algorithms:
                if not self._is_regex_pattern(algorithm):
                    # check if string matches exactly
                    if algorithm == docker_image_name:
                        found = True
                else:
                    expr_ = re.compile(algorithm)
                    if expr_.match(docker_image_name):
                        found = True

            if not found:
                self.log.warn(
                    "A task was sent with a docker image that this"
                    " node does not allow to run."
                )
                return False

        # check if user or their organization is allowed
        allowed_users = self._policies.get("allowed_users", [])
        allowed_orgs = self._policies.get("allowed_organizations", [])
        if allowed_users or allowed_orgs:
            is_allowed = self.client.check_user_allowed_to_send_task(
                allowed_users,
                allowed_orgs,
                task_info["init_org"]["id"],
                task_info["init_user"]["id"],
            )
            if not is_allowed:
                self.log.warn(
                    "A task was sent by a user or organization that "
                    "this node does not allow to start tasks."
                )
                return False

        return True

    @staticmethod
    def _is_regex_pattern(pattern: str) -> bool:
        """
        Check if a string just a string or if it is a regex pattern. Note that there is
        no failsafe way to do this so we make a best effort.

        Note, for instance, that if a user provides the allowed algorithm "some.name",
        we will interpret this as a regular string. This prevents that "someXname" is
        allowed as well. The user is thus not able to define a regex pattern with only
        a dot as special character. However we expect that this use case is extremely
        rare - not doing so is likely to lead to regex's that lead to unintended
        algorithms passing the filter criteria.

        Parameters
        ----------
        pattern: str
            String to be checked

        Returns
        -------
        bool
            Returns False if the pattern is a normal string, True if it is a regex.
        """
        # Inspired by
        # https://github.com/corydolphin/flask-cors/blob/main/flask_cors/core.py#L254.
        common_regex_chars = [
            "*",
            "\\",
            "?",
            "$",
            "^",
            "[",
            "]",
            "(",
            ")",
            "{",
            "}",
            "|",
            "+",
            "\.",
        ]
        # Use common characters used in regular expressions as a proxy
        # for if this string is in fact a regex.
        return any((c in pattern for c in common_regex_chars))

    def is_running(self, run_id: int) -> bool:
        """
        Check if a container is already running for <run_id>.

        Parameters
        ----------
        run_id: int
            run_id of the algorithm container to be found

        Returns
        -------
        bool
            Whether or not algorithm container is running already
        """
        running_containers = self.docker.containers.list(
            filters={
                "label": [
                    f"{APPNAME}-type=algorithm",
                    f"node={self.node_name}",
                    f"run_id={run_id}",
                ]
            }
        )
        return bool(running_containers)

    def cleanup_tasks(self) -> list[KilledRun]:
        """
        Stop all active tasks

        Returns
        -------
        list[KilledRun]:
            List of information on tasks that have been killed
        """
        run_ids_killed = []
        if self.active_tasks:
            self.log.debug(f"Killing {len(self.active_tasks)} active task(s)")
        while self.active_tasks:
            task = self.active_tasks.pop()
            task.cleanup()
            run_ids_killed.append(
                KilledRun(
                    run_id=task.run_id, task_id=task.task_id, parent_id=task.parent_id
                )
            )
        return run_ids_killed

    def cleanup(self) -> None:
        """
        Stop all active tasks and delete the isolated network

        Note: the temporary docker volumes are kept as they may still be used
        by a parent container
        """
        # note: the function `cleanup_tasks` returns a list of tasks that were
        # killed, but we don't register them as killed so they will be run
        # again when the node is restarted
        self.cleanup_tasks()
        for service in self.linked_services:
            self.isolated_network_mgr.disconnect(service)

        # remove the node container from the network, it runs this code.. so
        # it does not make sense to delete it just yet
        self.isolated_network_mgr.disconnect(self.node_container_name)

        # remove the connected containers and the network
        self.isolated_network_mgr.delete(kill_containers=True)

    def run(
        self,
        run_id: int,
        task_info: dict,
        image: str,
        docker_input: bytes,
        tmp_vol_name: str,
        token: str,
        databases_to_use: list[str],
    ) -> tuple[TaskStatus, list[dict] | None]:
        """
        Checks if docker task is running. If not, creates DockerTaskManager to
        run the task

        Parameters
        ----------
        run_id: int
            Server run identifier
        task_info: dict
            Dictionary with task information
        image: str
            Docker image name
        docker_input: bytes
            Input that can be read by docker container
        tmp_vol_name: str
            Name of temporary docker volume assigned to the algorithm
        token: str
            Bearer token that the container can use
        databases_to_use: list[str]
            Labels of the databases to use

        Returns
        -------
        TaskStatus, list[dict] | None
            Returns a tuple with the status of the task and a description of
            each port on the VPN client that forwards traffic to the algorithm
            container (``None`` if VPN is not set up).
        """
        # Verify that an allowed image is used
        if not self.is_docker_image_allowed(image, task_info):
            msg = f"Docker image {image} is not allowed on this Node!"
            self.log.critical(msg)
            return TaskStatus.NOT_ALLOWED, None

        # Check that this task is not already running
        if self.is_running(run_id):
            self.log.warn("Task is already being executed, discarding task")
            self.log.debug(f"run_id={run_id} is discarded")
            return TaskStatus.ACTIVE, None

        # we pass self.docker instance, in which we may have logged in to registries
        task = DockerTaskManager(
            image=image,
            docker_client=self.docker,
            run_id=run_id,
            task_info=task_info,
            vpn_manager=self.vpn_manager,
            node_name=self.node_name,
            tasks_dir=self.__tasks_dir,
            isolated_network_mgr=self.isolated_network_mgr,
            databases=self.databases,
            docker_volume_name=self.data_volume_name,
            alpine_image=self.alpine_image,
            proxy=self.proxy,
            device_requests=self.algorithm_device_requests,
        )

        # attempt to kick of the task. If it fails do to unknown reasons we try
        # again. If it fails permanently we add it to the failed tasks to be
        # handled by the speaking worker of the node
        attempts = 1
        while not (task.status == TaskStatus.ACTIVE) and attempts < 3:
            try:
                vpn_ports = task.run(
                    docker_input=docker_input,
                    tmp_vol_name=tmp_vol_name,
                    token=token,
                    algorithm_env=self.algorithm_env,
                    databases_to_use=databases_to_use,
                )

            except UnknownAlgorithmStartFail:
                self.log.exception(
                    f"Failed to start run {run_id} for an "
                    "unknown reason. Retrying..."
                )
                time.sleep(1)  # add some time before retrying the next attempt

            except PermanentAlgorithmStartFail:
                break

            attempts += 1

        # keep track of the active container
        if has_task_failed(task.status):
            self.failed_tasks.append(task)
            return task.status, None
        else:
            self.active_tasks.append(task)
            return task.status, vpn_ports

    def get_result(self) -> Result:
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
        while (not finished_tasks) and (not self.failed_tasks):
            for task in self.active_tasks:
                try:
                    if task.is_finished():
                        finished_tasks.append(task)
                        self.active_tasks.remove(task)
                        break
                except AlgorithmContainerNotFound:
                    self.log.exception(
                        "Failed to find container for " "algorithm with run_id %s",
                        task.run_id,
                    )
                    self.failed_tasks.append(task)
                    self.active_tasks.remove(task)
                    break

            # sleep for a second before checking again
            time.sleep(1)

        if finished_tasks:
            # at least one task is finished

            finished_task = finished_tasks.pop()
            self.log.debug(f"Run id={finished_task.run_id} is finished")

            # Check exit status and report
            logs = finished_task.report_status()

            # Cleanup containers
            finished_task.cleanup()

            # Retrieve results from file
            results = finished_task.get_results()

            # remove the VPN ports of this run from the database
            self.client.request(
                "port", params={"run_id": finished_task.run_id}, method="DELETE"
            )
        else:
            # at least one task failed to start
            finished_task = self.failed_tasks.pop()
            logs = "Container failed. Check node logs for details"
            results = b""

        return Result(
            run_id=finished_task.run_id,
            task_id=finished_task.task_id,
            logs=logs,
            data=results,
            status=finished_task.status,
            parent_id=finished_task.parent_id,
        )

    def login_to_registries(self, registries: list = []) -> None:
        """
        Login to the docker registries

        Parameters
        ----------
        registries: list
            list of registries to login to
        """
        for registry in registries:
            try:
                self.docker.login(
                    username=registry.get("username"),
                    password=registry.get("password"),
                    registry=registry.get("registry"),
                )
                self.log.info(f"Logged in to {registry.get('registry')}")
            except docker.errors.APIError as e:
                self.log.warn(f"Could not login to {registry.get('registry')}")
                self.log.debug(e)

    def link_container_to_network(self, container_name: str, config_alias: str) -> None:
        """
        Link a docker container to the isolated docker network

        Parameters
        ----------
        container_name: str
            Name of the docker container to be linked to the network
        config_alias: str
            Alias of the docker container defined in the config file
        """
        container = get_container(docker_client=self.docker, name=container_name)
        if not container:
            self.log.error(
                f"Could not link docker container {container_name} "
                "that was specified in the configuration file to "
                "the isolated docker network."
            )
            self.log.error("Container not found!")
            return
        self.isolated_network_mgr.connect(
            container_name=container_name, aliases=[config_alias]
        )
        self.linked_services.append(container_name)

    def kill_selected_tasks(
        self, org_id: int, kill_list: list[ToBeKilled] = None
    ) -> list[KilledRun]:
        """
        Kill tasks specified by a kill list, if they are currently running on
        this node

        Parameters
        ----------
        org_id: int
            The organization id of this node
        kill_list: list[ToBeKilled]
            A list of info about tasks that should be killed.

        Returns
        -------
        list[KilledRun]
            List with information on killed tasks
        """
        killed_list = []
        for container_to_kill in kill_list:
            if container_to_kill["organization_id"] != org_id:
                continue  # this run is on another node
            # find the task
            task = next(
                (
                    t
                    for t in self.active_tasks
                    if t.run_id == container_to_kill["run_id"]
                ),
                None,
            )
            if task:
                self.log.info(f"Killing containers for run_id={task.run_id}")
                self.active_tasks.remove(task)
                task.cleanup()
                killed_list.append(
                    KilledRun(
                        run_id=task.run_id,
                        task_id=task.task_id,
                        parent_id=task.parent_id,
                    )
                )
            else:
                self.log.warn(
                    "Received instruction to kill run_id="
                    f"{container_to_kill['run_id']}, but it was not "
                    "found running on this node."
                )
        return killed_list

    def kill_tasks(
        self, org_id: int, kill_list: list[ToBeKilled] = None
    ) -> list[KilledRun]:
        """
        Kill tasks currently running on this node.

        Parameters
        ----------
        org_id: int
            The organization id of this node
        kill_list: list[ToBeKilled] (optional)
            A list of info on tasks that should be killed. If the list
            is not specified, all running algorithm containers will be killed.

        Returns
        -------
        list[KilledRun]
            List of dictionaries with information on killed tasks
        """
        if kill_list:
            killed_runs = self.kill_selected_tasks(org_id=org_id, kill_list=kill_list)
        else:
            # received instruction to kill all tasks on this node
            self.log.warn(
                "Received instruction from server to kill all algorithms "
                "running on this node. Executing that now..."
            )
            killed_runs = self.cleanup_tasks()
            if len(killed_runs):
                self.log.warn(
                    "Killed the following run ids as instructed via socket:"
                    f" {', '.join([str(r.run_id) for r in killed_runs])}"
                )
            else:
                self.log.warn("Instructed to kill tasks but none were running")
        return killed_runs

    def get_column_names(self, label: str, type_: str) -> list[str]:
        """
        Get column names from a node database

        Parameters
        ----------
        label: str
            Label of the database
        type_: str
            Type of the database

        Returns
        -------
        list[str]
            List of column names
        """
        db = self.databases.get(label)
        if not db:
            self.log.error("Database with label %s not found", label)
            return []
        if not db["is_file"]:
            self.log.error(
                "Database with label %s is not a file. Cannot"
                " determine columns without query",
                label,
            )
            return []
        if db["type"] == "excel":
            self.log.error(
                "Cannot determine columns for excel database " " without a worksheet"
            )
            return []
        if type_ not in ("csv", "sparql"):
            self.log.error(
                "Cannot determine columns for database of type %s."
                "Only csv and sparql are supported",
                type_,
            )
            return []
        return get_column_names(db["uri"], type_)
