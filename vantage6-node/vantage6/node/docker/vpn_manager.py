import docker
import logging
import json
import time

from json.decoder import JSONDecodeError
from typing import List, Union, Dict
from docker.models.containers import Container

from vantage6.common.globals import APPNAME, VPN_CONFIG_FILE
from vantage6.node.util import logger_name
from vantage6.node.globals import (
    MAX_CHECK_VPN_ATTEMPTS, NETWORK_CONFIG_IMAGE, VPN_CLIENT_IMAGE,
    FREE_PORT_RANGE, DEFAULT_ALGO_VPN_PORT
)
from vantage6.node.docker.network_manager import IsolatedNetworkManager


class VPNManager(object):
    """
    Setup a VPN client in a Docker container and configure the network so that
    the VPN container can forward traffic to and from algorithm containers.
    """
    log = logging.getLogger(logger_name(__name__))

    def __init__(self, isolated_network_mgr: IsolatedNetworkManager,
                 node_name: str, vpn_volume_name: str, vpn_subnet: str):
        self.isolated_network_mgr = isolated_network_mgr
        self.vpn_client_container_name = f'{APPNAME}-{node_name}-vpn-client'
        self.vpn_volume_name = vpn_volume_name
        self.subnet = vpn_subnet

        self.has_vpn = False

        # Connect to docker daemon
        self.docker = docker.from_env()

    def connect_vpn(self) -> None:
        """
        Start VPN client container and configure network to allow
        algorithm-to-algoritm communication
        """
        self.log.debug("Mounting VPN configuration file")
        # add volume containing OVPN config file
        data_path = '/mnt/vpn/'  # TODO obtain from DockerNodeContext
        volumes = {
            self.vpn_volume_name: {'bind': data_path, 'mode': 'rw'},
        }
        # set environment variables
        vpn_config = data_path + VPN_CONFIG_FILE
        env = {'VPN_CONFIG': vpn_config}

        # if a VPN container is already running, kill and remove it
        self.vpn_client_container = self.check_running()
        # TODO refactor with other functions
        if self.vpn_client_container:
            self.log.warn("Removing VPN container that was already running")
            try:
                self.vpn_client_container.kill()
            except Exception as e:
                pass
            self.vpn_client_container.remove()

        # start vpnclient
        self.log.debug("Starting VPN client container")
        self.vpn_client_container = self.docker.containers.run(
            image=VPN_CLIENT_IMAGE,
            command="",  # commands to run are already defined in docker image
            volumes=volumes,
            detach=True,
            environment=env,
            restart_policy={"Name": "always"},
            name=self.vpn_client_container_name,
            cap_add=['NET_ADMIN', 'SYSLOG'],
            devices=['/dev/net/tun'],
        )

        # attach vpnclient to isolated network
        self.log.debug("Connecting VPN client container to isolated network")
        self.isolated_network_mgr.connect(
            container_name=self.vpn_client_container_name,
            aliases=[self.vpn_client_container_name]
        )

        # create network exception so that packet transfer between VPN network
        # and the vpn client container is allowed
        bridge_interface = self._find_isolated_bridge()
        self._configure_host_network(isolated_bridge=bridge_interface)

        # set successful initiation of VPN connection
        self.has_vpn = True
        self.log.debug("VPN client container started")

    def check_running(self) -> Container:
        """
        Check if VPN container exists

        Returns
        -------
        Container or None
            VPN container if it exists, else None
        TODO refactor?!
        """
        running_containers = self.docker.containers.list(all=True, filters={
            "name": self.vpn_client_container_name
        })
        return running_containers[0] if running_containers else None

    def has_connection(self) -> bool:
        """ Return True if VPN connection is active """
        if not self.has_vpn:
            return False
        # check if the VPN container has an IP address in the VPN namespace
        try:
            # if there is a VPN connection, the following command will return
            # a json vpn interface. If not, it will return "Device "tun0" does
            # not exist."
            _, vpn_interface = self.vpn_client_container.exec_run(
                'ip --json addr show dev tun0'
            )
            vpn_interface = json.loads(vpn_interface)
        except JSONDecodeError:
            return False
        return True

    def exit_vpn(self) -> None:
        """
        Gracefully shutdown the VPN and clean up
        """
        if not self.has_vpn:
            return
        self.has_vpn = False
        self.log.debug("Stopping and removing the VPN client container")
        try:
            self.vpn_client_container.kill()
        except Exception as e:
            self.log.warn("Tried to kill VPN container but it was not running")
        self.vpn_client_container.remove()

        # Clean up host network changes. We have added two rules to the front
        # of the DOCKER-USER chain. Now we remove the first two rules (which is
        # done by removing rule number 1 twice)
        command = \
            'sh -c "iptables -D DOCKER-USER 1; iptables -D DOCKER-USER 1;"'
        self.docker.containers.run(
            image=NETWORK_CONFIG_IMAGE,
            network='host',
            cap_add='NET_ADMIN',
            command=command,
            remove=True,
        )

    def get_vpn_ip(self) -> str:
        """
        Get VPN IP address in VPN server namespace

        Returns
        -------
        str
            IP address assigned to VPN client container by VPN server
        """
        # VPN might not be fully set up at this point. Therefore, poll to
        # check. When it is ready, extract the IP address.
        n_attempt = 0
        while n_attempt < MAX_CHECK_VPN_ATTEMPTS:
            n_attempt += 1
            try:
                _, vpn_interface = self.vpn_client_container.exec_run(
                    'ip --json addr show dev tun0'
                )
                vpn_interface = json.loads(vpn_interface)
                break
            except (JSONDecodeError, docker.errors.APIError):
                # JSONDecodeError if VPN is not setup yet, APIError if VPN
                # container is restarting (e.g. due to connection errors)
                time.sleep(1)
        return vpn_interface[0]['addr_info'][0]['local']

    def forward_vpn_traffic(self, helper_container: Container,
                            algo_image_name: str) -> int:
        """
        Setup rules so that traffic is properly forwarded between the VPN
        container and the algorithm container (and its helper container)

        Parameters
        ----------
        algo_helper_container: Container
            Helper algorithm container
        algo_image_name: str
            Name of algorithm image that is run

        Returns
        -------
        int
            Port on the VPN client that forwards traffic to the algo container
        """
        vpn_port = self._forward_traffic_to_algorithm(
            helper_container, algo_image_name)
        self._forward_traffic_from_algorithm(helper_container)
        return vpn_port

    def _forward_traffic_from_algorithm(
            self, algo_helper_container: Container) -> None:
        """
        Direct outgoing algorithm container traffic to the VPN client container

        Parameters
        ----------
        algo_helper_container: Container
            Helper algorithm container
        """
        if not self.has_vpn:
            return  # ignore if VPN is not active
        vpn_local_ip = self.isolated_network_mgr.get_container_ip(
            self.vpn_client_container_name
        )
        if not vpn_local_ip:
            self.log.error("VPN client container not found, turning off VPN")
            self.has_vpn = False
            return

        network = 'container:' + algo_helper_container.id

        # add IP route line to the algorithm container network
        cmd = f"ip route replace default via {vpn_local_ip}"
        self.docker.containers.run(
            image='alpine',
            network=network,
            cap_add='NET_ADMIN',
            command=cmd,
            remove=True
        )

    def _forward_traffic_to_algorithm(self, algo_helper_container: Container,
                                      algo_image_name: str) -> int:
        """
        Forward incoming traffic from the VPN client container to the
        algorithm container

        Parameters
        ----------
        algo_helper_container: Container
            Helper algorithm container
        algo_image_name: str
            Name of algorithm image that is run

        Returns
        -------
        int
            Port on the VPN client that forwards traffic to the algo container
        """
        if not self.has_vpn:
            return None  # no port assigned if no VPN is available
        # Find ports on VPN container that are already occupied
        cmd = (
            'sh -c '
            '"iptables -t nat -L PREROUTING | awk \'{print $7}\' | cut -c 5-"'
        )
        occupied_ports = self.vpn_client_container.exec_run(cmd=cmd)
        occupied_ports = occupied_ports.output.decode('utf-8')
        occupied_ports = occupied_ports.split('\n')
        occupied_ports = \
            [int(port) for port in occupied_ports if port is not '']

        # take first available port
        vpn_client_port_options = set(FREE_PORT_RANGE) - set(occupied_ports)
        vpn_client_port = next(iter(vpn_client_port_options))

        # Get IP Address of the algorithm container
        algo_helper_container.reload()  # update attributes
        algo_ip = (
            algo_helper_container.attrs['NetworkSettings']['Networks']
                                       [self.isolated_network_mgr.network_name]
                                       ['IPAddress']
        )
        # Set port at which algorithm containers receive traffic
        algorithm_port = self._find_exposed_port(algo_image_name)

        # Set up forwarding VPN traffic to algorithm container
        command = (
            'sh -c '
            '"iptables -t nat -A PREROUTING -i tun0 -p tcp '
            f'--dport {vpn_client_port} -j DNAT '
            f'--to {algo_ip}:{algorithm_port}"'
        )
        self.vpn_client_container.exec_run(command)
        return vpn_client_port

    def _find_exposed_port(self, image: str) -> str:
        """
        Find which ports were exposed via the EXPOSE keyword in the dockerfile
        of the algorithm image. This port will be used for VPN traffic. If no
        port is specified, the default port is used

        Parameters
        ----------
        image: str
            Algorithm image name

        Returns
        -------
        str:
            Port number to forward VPN traffic to (as str)
        """
        n2n_image = self.docker.images.get(image)
        port = DEFAULT_ALGO_VPN_PORT

        exposed_ports = []
        try:
            exposed_ports = n2n_image.attrs['Config']['ExposedPorts']
        except KeyError:
            return port  # No exposed ports defined, use default

        if len(exposed_ports) == 1:
            port = list(exposed_ports)[0]
            port = port[0:port.find('/')]
            try:
                int(port)
            except ValueError:
                self.log.warn("Could not parse port specified in algorithm "
                              f"docker image {image}: {port}. Using default "
                              f"port {DEFAULT_ALGO_VPN_PORT}")
                return DEFAULT_ALGO_VPN_PORT
        elif len(exposed_ports) > 1:
            self.log.warn("More than 1 port exposed in docker image. "
                          f"Using default port {port}.")
        # else: no exposed port specified, return default
        return port

    def _find_isolated_bridge(self) -> str:
        """
        Retrieve the linked network interface in the host namespace for
        network interface eth0 in the container namespace.

        Returns
        -------
        string
            The name of the network interface in the host namespace
        """
        # Get network config from VPN client container
        _, isolated_interface = self.vpn_client_container.exec_run(
            ['ip', '--json', 'addr', 'show', 'dev', 'eth0']
        )

        isolated_interface = json.loads(isolated_interface)
        link_index = self._get_link_index(isolated_interface)

        # Get network config from host namespace
        host_interfaces = self.docker.containers.run(
            image=NETWORK_CONFIG_IMAGE,
            network='host',
            command=['ip', '--json', 'addr'],
            remove=True
        )
        host_interfaces = json.loads(host_interfaces)

        linked_interface = self._get_if(host_interfaces, link_index)
        bridge_interface = linked_interface['master']
        return bridge_interface

    def _configure_host_network(self, isolated_bridge: str) -> None:
        """
        By default the internal bridge networks are configured to prohibit
        packet forwarding between networks. Create an exception to this rule
        for forwarding traffic between the bridge and vpn network.

        Parameters
        ----------
        vpn_subnet: string
            Subnet of allowed VPN IP addresses
        isolated_bridge: string
            Name of the network interface in the host namespace
        """
        self.log.debug("Configuring host network exceptions for VPN")
        # The following command inserts rules that traffic from the VPN subnet
        # will be accepted into the isolated network
        command = (
            'sh -c "'
            f'iptables -I DOCKER-USER 1 -d {self.subnet} -i {isolated_bridge} '
            '-j ACCEPT; '
            f'iptables -I DOCKER-USER 1 -s {self.subnet} -o {isolated_bridge} '
            '-j ACCEPT; '
            '"'
        )

        self.docker.containers.run(
            image=NETWORK_CONFIG_IMAGE,
            network='host',
            cap_add='NET_ADMIN',
            command=command,
            # auto_remove=True,
            # # TODO figure out why this needs to be commented out (leads to
            # crash otherwise)
        )

    def _get_if(self, interfaces, index) -> Union[Dict, None]:
        """ Get interface configuration based on interface index """
        for interface in interfaces:
            if int(interface['ifindex']) == index:
                return interface

        return None

    def _get_link_index(self, if_json: Union[Dict, List]) -> int:
        if isinstance(if_json, list):
            if_json = if_json[-1]
        return int(if_json['link_index'])
