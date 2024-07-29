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
from docker.utils import parse_repository_tag

from typing import NamedTuple
from pathlib import Path

from vantage6.common import logger_name
from vantage6.common import get_database_config
from vantage6.common.docker.addons import (
    get_container,
    get_digest,
    get_image_name_wo_tag,
    running_in_docker,
)
from vantage6.common.globals import APPNAME, BASIC_PROCESSING_IMAGE, NodePolicy
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
from vantage6.node.globals import DEFAULT_REQUIRE_ALGO_IMAGE_PULL
from vantage6.common.configuration_manager import DictNamesIds

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
        self.log.debug("Databases: %s", self.databases)

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
        if not policies or (
            not policies.get(NodePolicy.ALLOWED_ALGORITHMS)
            and not policies.get(NodePolicy.ALLOWED_ALGORITHM_STORES)
        ):
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
            self.log.debug("Volume %s already exists.", volume_name)

        except docker.errors.NotFound:
            self.log.debug("Creating volume %s", volume_name)
            self.docker.volumes.create(volume_name)

    def _check_pol_org(
        self,
        init_org_id: int,
    ) -> bool:
        """
        Check if execution of the task is allowed by the organizations allowlist policy

        Parameters
        ----------
        init_org_id: int
            ID of the organization that initiated the task

        Returns
        -------
        bool
            True if policy allows execution, False otherwise
        """
        # NOTE/TODO: we assume node config has been properly validated, this
        # means that validation should better be done at the vantage6-node
        # level, not vantage6-cli
        allowed_orgs = self._policies.get(NodePolicy.ALLOWED_ORGANIZATIONS, False)

        if not allowed_orgs:
            self.log.info("No allowed organizations policy set. All organizations are allowed to send tasks.")
            return True

        allowed_orgs_ids = allowed_orgs.get("ids", [])
        allowed_orgs_names = allowed_orgs.get("names", [])

        self.log.debug(
            "Allowed organizations: %s", allowed_orgs_ids + allowed_orgs_names
        )
        self.log.debug("Initiating organization: %s", init_org_id)

        if allowed_orgs_ids:
            # check against allowed ids
            if init_org_id in allowed_orgs_ids:
                self.log.info(
                    "Initiating organization with ID %s is in allowed organizations: %s",
                    init_org_id, allowed_orgs_ids
                )
                return True

        if allowed_orgs_names:
            # if config has org names, we need to get name of init org from its id
            init_org = self.client.request(f'organization/{init_org_id}', method='GET')
            if 'name' in init_org and init_org.get('name') in allowed_orgs_names:
                self.log.info(
                    "Initiating organization with ID %s is in allowed organizations: %s",
                    init_org_id, allowed_orgs_names
                )
                return True

        self.log.error(
            "Initiating organization with ID %s not in allowed organizations: %s",
            init_org_id, allowed_orgs_ids + allowed_orgs_names
        )
        return False

    def _check_pol_user(
        self,
        init_user_id: int,
    ) -> bool:
        """
        Check if the user is allowed to send a task to this node

        Parameters
        ----------
        allowed_users: DictNamesIds
            List of allowed user IDs
        init_user_id: int
            ID of the user that initiated the task

        Returns
        -------
        bool
            Whether or not the user is allowed to send a task to this node
        """
        allowed_users = self._policies.get(NodePolicy.ALLOWED_USERS, False)

        # ultimate decision
        allowed = False

        # TODO: Do we want to make this more explicit to the node admin?
        if not allowed_users:
            self.log.info("No allowed users policy set. All users allows to send tasks.")
            return True

        # NOTE/TODO: we assume node config has been properly validated, this
        # means that validation should better be done at the vantage6-node
        # level, not vantage6-cli
        allowed_users_ids = allowed_users.get("ids", [])
        if init_user_id in allowed_users_ids:
            self.log.info(
                "Initiating user with ID %s is in allowed users: %s",
                init_user_id, allowed_users_ids
            )
            allowed = True

        self.log.error(
            "Initiating user with ID %s not in allowed users: %s",
            init_user_id, allowed_users_ids
        )


        # TODO: below is old comment, but confirm it is still the case that
        # node does not have permission to access user information, hence not
        # possible to check user name
        # # TODO it would be nicer to check all users in a single request
        # # but that requires other multi-filter options in the API
        # # TODO this option is now disabled since nodes do not have permission
        # # to access user information. We need to decide if we want to give them
        # # that permission for this.
        # # ----------------------------------------------------------
        # # check if task-initiating user name is in allowed users
        # # for user in allowed_users:
        # #     resp = self.request("user", params={"username": user})
        # #     print(resp)
        # #     for d in resp:
        # #         if d.get("username") == user and d.get("id") == init_user_id:
        # #             return True

        return allowed

    def _check_pol_allowlist(self, req_image: str) -> bool:
        """
        Check if a requested image is allowed by the allowlist algorithm policy.

        Parameters
        ----------
        req_image: str
            docker image name of the requested image to be checked

        Returns
        -------
        bool
            True if policy allows for execution, False otherwise
        """
        allowed_algorithms = self._policies.get(NodePolicy.ALLOWED_ALGORITHMS, False)

        if not allowed_algorithms:
            self.log.warn("No allowed algorithms policy set. All algorithms are allowed!")
            return True

        # ultimate decision for allowlist policy
        allowed = False

        try:
            req_image_wo_tag = get_image_name_wo_tag(req_image)
        except Exception as exc:
            self.log.warning(
                "Could not parse image with name %s: %s",
                req_image,
                exc,
            )
            req_image_wo_tag = None

        # TODO v5+: would be nice if there if we had a configuration loader
        # that parses, transforms, and validates config at the node level
        if isinstance(allowed_algorithms, str):
            allowed_algorithms = [allowed_algorithms]

        for allowed_algo in allowed_algorithms:
            # TODO v5+: we'd rather have the node admin be explicit about if
            # they are using a regex or a string in their policies
            if not self._is_regex_pattern(allowed_algo):
                try:
                    allowed_wo_tag = get_image_name_wo_tag(allowed_algo)
                except Exception as exc:
                    self.log.warning(
                        "Could not parse allowed_algorithm policy with name %s: %s",
                        allowed_algo,
                        exc,
                    )
                    self.log.warning("Skipping policy as it cannot be parsed")
                    # skip policy as it cannot be parsed
                    continue
                if allowed_algo == req_image:
                    # OK if allowed algorithm and provided algorithm match exactly
                    allowed = True
                    break
                elif allowed_algo == req_image_wo_tag:
                    # OK if allowed algorithm is an image name without a tag, and
                    # the provided image is the same but includes extra tag
                    allowed = True
                    break
                elif allowed_wo_tag == req_image_wo_tag:
                    # The allowed image and the evaluated image are indeed the same
                    # image but the allowed image only allows certain tags or sha's.
                    # Gather the digests of the images and compare them - if they
                    # are the same, the image is allowed.
                    # Note that by comparing the digests, we also take into account
                    # the situation where e.g. the allowed image has a tag, but the
                    # evaluated image has a sha256.
                    digest_evaluated_image = get_digest(
                        req_image, client=self.docker
                    )
                    if not digest_evaluated_image:
                        self.log.warning(
                            "Could not obtain digest for image %s",
                            req_image,
                        )
                    digest_policy_image = get_digest(
                        allowed_algo, client=self.docker
                    )
                    if not digest_policy_image:
                        self.log.warning(
                            "Could not obtain digest for image %s", allowed_algo
                        )
                    if (
                        digest_evaluated_image
                        and digest_policy_image
                        and (digest_evaluated_image == digest_policy_image)
                    ):
                        allowed = True
                        break
            else:
                expr_ = re.compile(allowed_algo)
                if expr_.match(req_image):
                    allowed = True

        return allowed


    def _check_pol_store(self, req_image: str, store_id) -> bool:
        """
        Check if a requested image is allowed by the store policy.

        Parameters
        ----------
        allowed_stores = self._policies.get(NodePolicy.ALLOWED_ALGORITHM_STORES)

        Returns
        -------
        bool
            True if policy allows for execution, False otherwise
        """
        allowed_stores = self._policies.get(NodePolicy.ALLOWED_ALGORITHM_STORES, False)

        if not allowed_stores:
            self.log.warn("No allowed stores policy set. All stores are allowed!")
            return True

        # TODO: What is store ID? Is it an integer? if so int 0 would be False
        if not store_id:
            self.log.warn("No store ID was provided in the task.")
            return False

        # ultimate decision for store policy
        allowed = False

        store = self.client.algorithm_store.get(store_id)
        store_from_task = store["url"]
        # check if the store matches any of the regex cases
        if isinstance(allowed_stores, str):
            allowed_stores = [allowed_stores]
        for store in allowed_stores:
            if not self._is_regex_pattern(store):
                # check if string matches exactly
                if store == store_from_task:
                    allowed = True
                    break
            else:
                expr_ = re.compile(store)
                if expr_.match(store_from_task):
                    allowed = True
                    break

        return allowed

    def _check_pol_basics(self, req_image: str) -> bool:
        """
        Check if a requested image is allowed by the basics alogirthm policy.

        Parameters
        ----------
        req_image: str
            docker image name of the requested image to be checked

        Returns
        -------
        bool
            True if policy allows, False otherwise
        """
        allow_basics = self._policies.get(NodePolicy.ALLOW_BASICS_ALGORITHM, True)

        if req_image.startswith(BASIC_PROCESSING_IMAGE):
            if allow_basics:
                return True
            else:
                self.log.warn(
                    "A task was sent with a basics algorithm that "
                    "this node does not allow to run."
                )

        return False


    def is_task_allowed(self, req_image: str, task_info: dict) -> bool:
        """
        Checks if a task is allowed to run on this node.

        Several task details such as the docker image name, initiaing user, or
        initiating organization are checked against policies defined by the
        node administrator.

        Parameters
        ----------
        req_img: str
            URI of the docker image of which we are checking if it is allowed
        task_info: dict
            Dictionary with information about the task

        Returns
        -------
        bool
            True if the task is allowed to run, False otherwise
        """
        # TODO: we currently presume that if the node admin has not set a
        # certain pocily, that certain policy is allow everything by it.
        # We might want to make this more explicit.
        # TODO: let the node admin choose how the different policies should be
        # combined and evaluated accordingly.

        # ultimate decision
        allowed = False

        # policies for how the indivual policies come together
        allow_either_whitelist_or_store = self._policies.get(
            "allow_either_whitelist_or_store", False
        )
        allow_either_org_or_user = self._policies.get(
            "allow_either_org_or_user", False
        )

        # basics algorithm policy
        checks_pol_basics = self._check_pol_basics(req_image)
        # passing the basics policy means the requested image is a basic
        # algorithms and the node allows it to run
        if checks_pol_basics:
            return True

        # initiating organizaion and user policies
        checks_pol_user = self._check_pol_user(task_info["init_user"]["id"])
        checks_pol_org = self._check_pol_org(task_info["init_org"]["id"])
        if allow_either_org_or_user:
            allowed = checks_pol_user or checks_pol_org
        else:
            allowed = checks_pol_user and checks_pol_org

        # allowed algorithms policy based on allowlists and algorithm stores
        checks_pol_allowlist = self._check_pol_allowlist(req_image)
        store_id = None
        if algorithm_store := task_info.get("algorithm_store"):
            store_id = algorithm_store.get("id")
        checks_pol_store = self._check_pol_store(req_image, store_id)
        if allow_either_whitelist_or_store:
            # if we allow an algorithm if it is defined in the whitelist or the store,
            # we return True if either the algorithm or the store is whitelisted
            allowed &= checks_pol_allowlist or checks_pol_store
        else:
            # only allow algorithm if it is allowed for both the allowed_algorithms and
            # the allowed_algorithm_stores
            allowed &= checks_pol_allowlist and checks_pol_store

        if not allowed:
            self.log.warning(
                "This node does not allow the algorithm %s to run!", req_image
            )

        return allowed

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
            self.log.debug("Killing %s active task(s)", len(self.active_tasks))
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
        if not self.is_task_allowed(image, task_info):
            msg = f"Docker image {image} is not allowed on this Node!"
            self.log.critical(msg)
            return TaskStatus.NOT_ALLOWED, None

        # Check that this task is not already running
        if self.is_running(run_id):
            self.log.info("Task is already being executed, discarding task")
            self.log.debug("run_id=%s is discarded", run_id)
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
            requires_pull=self._policies.get(
                NodePolicy.REQUIRE_ALGORITHM_PULL, DEFAULT_REQUIRE_ALGO_IMAGE_PULL
            ),
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
            self.log.debug("Run id=%s is finished", finished_task.run_id)

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
                self.log.warning(f"Could not login to {registry.get('registry')}")
                self.log.warning(e)

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
                "Cannot determine columns for excel database without a worksheet"
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
