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
import pathlib
import re
import json
from typing import NamedTuple, List, Union, Dict
from jwt.algorithms import Algorithm

from vantage6.common.docker_addons import pull_if_newer
from vantage6.common.globals import APPNAME
from vantage6.node.util import logger_name


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

    def __init__(self, allowed_images, tasks_dir, isolated_network_name: str,
                 node_name: str, data_volume_name: str) -> None:
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

        # Connect to docker daemon
        # self.docker = docker.DockerClient(base_url=docker_socket_path)
        self.docker = docker.from_env()

        # keep track of the running containers
        self.active_tasks = []

        # before a task is executed it gets exposed to these regex
        self._allowed_images = allowed_images

        # create / get isolated network to which algorithm containers
        # can attach
        self.network_name = isolated_network_name
        self._isolated_network = self._create_network()

        # node name is used to identify algorithm containers belonging
        # to this node. This is required as multiple nodes may run at
        # a single machine sharing the docker daemon while using a
        # different server. Using a different server means that there
        # could be duplicate result_id's running at the node at the same
        # time.
        self.node_name = node_name

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
            self.__tasks_dir,
            "task-{0:09d}".format(result_id)
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

    def _create_network(self) -> docker.models.networks.Network:
        """ Creates an internal (docker) network

            Used by algorithm containers to communicate with the node API.
        """
        name = self.network_name

        try:
            network = self.docker.networks.get(name)
            self.log.debug(f"Network {name} already exists. Deleting it.")
            network.remove()
        except Exception:
            self.log.debug("No network found...")

        self.log.debug(f"Creating isolated docker-network {name}!")

        internal_ = self.running_in_docker()
        if not internal_:
            self.log.warn(
                "Algorithms have internet connection! "
                "This happens because you use 'vnode-local'!"
            )

        network = self.docker.networks.create(
            name,
            driver="bridge",
            internal=internal_,
            scope="local"
        )

        return network

    def connect_to_isolated_network(self, container_name, aliases):
        """Connect to the isolated network."""
        msg = f"Connecting to isolated network '{self.network_name}'"
        self.log.debug(msg)

        # If the network already exists, this is a no-op.
        self._isolated_network.connect(container_name, aliases=aliases)

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
        """Return True iff a container is already running for <result_id>."""
        container = self.docker.containers.list(filters={
            "label": [
                f"{APPNAME}-type=algorithm",
                f"node={self.node_name}",
                f"result_id={result_id}"
            ]
        })

        return container

    def pull(self, image):
        """Pull the latest image."""
        try:
            self.log.info(f"Retrieving latest image: '{image}'")
            # self.docker.images.pull(image)
            pull_if_newer(self.docker, image, self.log)

        except Exception as e:
            self.log.debug('Failed to pull image')
            self.log.error(e)

    def set_database_uri(self, database_uri):
        """A setter for clarity."""
        self.database_uri = database_uri

    def run(self, result_id: int,  image: str, docker_input: bytes,
            tmp_vol_name: int, token: str) -> bool:
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
            return False

        # Check that this task is not already running
        if self.is_running(result_id):
            self.log.warn("Task is already being executed, discarding task")
            self.log.debug(f"result_id={result_id} is discarded")
            return False

        # Try to pull the latest image
        self.pull(image)

        # FIXME: We should have a seperate mount/volume for this. At the
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
        #   in some way.
        tmp_folder = "/mnt/tmp"
        data_folder = "/mnt/data"

        volumes = {
            tmp_vol_name: {"bind": tmp_folder, "mode": "rw"},
        }

        if self.running_in_docker():
            volumes[self.data_volume_name] = \
                {"bind": data_folder, "mode": "rw"}

        else:
            volumes[self.__tasks_dir] = {"bind": data_folder, "mode": "rw"}

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

        self.log.debug(f"volumes: {volumes}")

        # attempt to run the image
        try:
            self.log.info(f"Run docker image={image}")
            container = self.docker.containers.run(
                image,
                detach=True,
                environment=environment_variables,
                network=self._isolated_network.name,
                volumes=volumes,
                labels={
                    f"{APPNAME}-type": "algorithm",
                    "node": self.node_name,
                    "result_id": str(result_id)
                }
            )
        except Exception as e:
            self.log.error('Could not run docker image!?')
            self.log.error(e)
            return False

        # setup forwarding of traffic VPN client to the algo container:
        vpn_port = self._forward_vpn_traffic(algo_container=container)
        # Direct algorithm container traffic to the VPN
        self._route_algo_container_to_vpn()

        # keep track of the container
        self.active_tasks.append({
            "result_id": result_id,
            "container": container,
            "output_file": os.path.join(task_folder_path, "output")
        })

        return vpn_port

    def _route_algo_container_to_vpn(self):
        # get address of the vpn client

        # TODO is this part relevant? (copied from other function)
        # container = self.docker.containers.get(self.vpn_client_container_name)
        # _, vpn_ip_info = container.exec_run(
        #     ['ip', '--json', 'addr', 'show', 'dev', 'eth0']
        # )
        cmd = "ip --json addr show dev eth0"
        vpn_ip_info = self.docker.containers.run(
            image='network-config',
            network=self._isolated_network.name,
            cap_add='NET_ADMIN',
            command=cmd,
            # auto_remove=True,
        )
        vpn_ip_info = json.loads(vpn_ip_info)
        print('vpn_ip_info')
        print(vpn_ip_info)

        gateway = vpn_ip_info[0]['addr_info'][0]['local']
        print('gateway')
        print(gateway)

        cmd = f"ip route replace default via {gateway}"
        self.docker.containers.run(
            image='alpine',
            network=self._isolated_network.name,
            cap_add='NET_ADMIN',
            command=cmd,
            # auto_remove=True,
        )

    def _forward_vpn_traffic(self, algo_container):
        # TODO no constants here
        _NETWORK_CONFIG_IMAGE = 'network-config'


        # get port on the vpn client container to forward from. This port
        # should not yet be occupied
        self.vpn_client_container.reload()
        occupied_client_ports = \
            self.vpn_client_container.attrs['NetworkSettings']['Ports']
        vpn_client_port_options = \
            set(range(49152, 65535)) - set(occupied_client_ports)
        vpn_client_port = next(iter(vpn_client_port_options))

        # TODO prepare for the case that the algorithm container is not
        # running, e.g. due to an error in the algorithm or because it finished
        #  in 1second. Then the required settings are probably not available

        # Get IP Address of the algorithm container
        algo_container.reload()  # update attributes
        algorithm_container_ip = (
            algo_container.attrs['NetworkSettings']['Networks']
                                [self._isolated_network.name]['IPAddress']
        )
        algorithm_port = '8888'

        # Set up
        command = (
            'sh -c "'
            'iptables -t nat -A PREROUTING -i tun0 -p tcp '
            f'--dport {vpn_client_port} -j DNAT '
            f'--to {algorithm_container_ip}:{algorithm_port}'
            '"'
        )

        self.docker.containers.run(
            image=_NETWORK_CONFIG_IMAGE,
            network=self._isolated_network.name,
            cap_add='NET_ADMIN',
            command=command,
            auto_remove=True,
        )
        # TODO clean up routing rules
        return vpn_client_port

    def get_result(self):
        """ Returns the oldest (FIFO) finished docker container.

            This is a blocking method until a finished container shows up.
            Once the container is obtained and the results are read, the
            container is removed from the docker environment.
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

    def running_in_docker(self):
        """Return True if this code is executed within a Docker container."""
        return pathlib.Path('/.dockerenv').exists()

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

    def connect_vpn(self, ovpn_file):
        # define mounting of config file
        ovpn_config_mounted_loc = '/data/vpn-config.ovpn.conf'
        volumes = {
            ovpn_file: {'bind': ovpn_config_mounted_loc, 'mode': 'rw'}
        }
        # set environment variables
        env = {
            'VPN_CONFIG': ovpn_config_mounted_loc
        }

        # start vpnclient
        # TODO define names below properly...
        # TODO maybe check if docker container vpn client is still running,
        # otherwise stop and remove it
        self.vpn_client_container_name = 'vtg6-vpn-client-container'
        self.vpn_client_container = self.docker.containers.run(
            image='algorithm-container-network_openvpn-client',
            command="",  # commands to run are already defined in docker image
            volumes=volumes,
            detach=True,
            environment=env,
            name=self.vpn_client_container_name,
            cap_add=['NET_ADMIN', 'SYSLOG'],
            devices=['/dev/net/tun'],
        )
        # self.vpn_client_container.reload()
        # print(self.vpn_client_container.attrs)
        # raise

        # attach vpnclient to isolated network
        self.connect_to_isolated_network(
            container_name=self.vpn_client_container.name,
            aliases=['vtg6-vpn-client-container']
        )

        # create network exception so that packet transfer between VPN network
        # and the vpn client container is allowed
        bridge_interface = self.find_isolated_bridge(
            self.vpn_client_container.name
        )
        self.configure_host_namespace(
            vpn_subnet=self.get_subnet(),
            isolated_bridge=bridge_interface
        )

    # TODO get the VPN IP address
    def get_vpn_ip(self):
        # self, container: str, command: Union[list, str]
        # # ):
        #     """ Run command in container

        #     Parameters
        #     ---------
        #     container: str
        #         Name or id of a running docker container
        #     command: str or list of str
        #         Command to execute

        #     Returns
        #     ------
        #     Output of the docker command
        #     """
        # TODO generalize (overlaps with find_isolated_bridge function also)
        container = self.docker.containers.get(self.vpn_client_container_name)
        _, vpn_info = container.exec_run(
            'ip --json addr show dev tun0'
            # ['ip', '--json', 'addr', 'show', 'dev', 'tun0']
        )
        print(_)
        print(vpn_info)
        vpn_info = json.loads(vpn_info)
        print(vpn_info)
        # from pprint import pprint
        # pprint(vpn_info)
        # raise

    def find_isolated_bridge(self, vpn_client_container: str):
        """
        Retrieve the linked network interface in the host namespace for network interface eth0 in the
        container namespace.

        :param container_id: container id of the docker container connected to an isolated network.
        :return: the name of the network interface in the host namespace
        """
        # TODO no constants here
        _NETWORK_CONFIG_IMAGE = 'network-config'
        _HOST = 'host'

        # Get network config from VPN client container
        container = self.docker.containers.get(vpn_client_container)
        _, isolated_interface = container.exec_run(
            ['ip', '--json', 'addr', 'show', 'dev', 'eth0']
        )

        isolated_interface = json.loads(isolated_interface)
        # print('isolated_interface')
        # print(isolated_interface)

        link_index = self._get_link_index(isolated_interface)
        # print('link_index')
        # print(link_index)

        # Get network config from host namespace
        host_interfaces = self.docker.containers.run(
            image=_NETWORK_CONFIG_IMAGE,
            network=_HOST,
            command=['ip', '--json', 'addr']
        )
        host_interfaces = json.loads(host_interfaces)
        # print('host_interfaces')
        # print(host_interfaces)

        linked_interface = self._get_if(host_interfaces, link_index)
        # print('linked_interface')
        # print(linked_interface)
        bridge_interface = linked_interface['master']
        # print('isolated_bridge')
        # print(bridge_interface)
        return bridge_interface

    def configure_host_namespace(self, vpn_subnet: str, isolated_bridge: str):
        """
        By default the internal bridge networks are configured to prohibit packet forwarding between
        networks. Create an exception to this rule for forwarding traffic between the bridge and vpn
        network.

        :param vpn_subnet:
        :param isolated_bridge:
        :return:
        """
        # TODO no constants here
        _NETWORK_CONFIG_IMAGE = 'network-config'

        # TODO remove comments
        # To look at this interactively, do something like:
        # docker run --rm -it --network host --cap-add NET_ADMIN --entrypoint sh network-config

        command = (
            'sh -c "'
            f'iptables -I DOCKER-USER 1 -d {vpn_subnet} -i {isolated_bridge} '
            '-j ACCEPT; '
            f'iptables -I DOCKER-USER 1 -s {vpn_subnet} -o {isolated_bridge} '
            '-j ACCEPT; '
            '"'
        )

        self.docker.containers.run(
            image=_NETWORK_CONFIG_IMAGE,
            network='host',
            cap_add='NET_ADMIN',
            command=command,
            auto_remove=True,
        )

    def get_subnet(self):
        # TODO get VPN IP range from config?!
        return '10.76.0.0/12'

    def _get_if(self, interfaces, index) -> Union[Dict, None]:
        """
        Get interface configuration based on interface index

        :param index:
        :return:
        """
        for interface in interfaces:
            if int(interface['ifindex']) == index:
                return interface

        return None

    def _get_link_index(self, if_json: Union[Dict, List]) -> int:
        if isinstance(if_json, list):
            if_json = if_json[-1]
        return int(if_json['link_index'])
