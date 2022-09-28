import docker
import logging
import json
import time

from json.decoder import JSONDecodeError
from typing import List, Union, Dict
from docker.models.containers import Container

from vantage6.common.globals import APPNAME, VPN_CONFIG_FILE
from vantage6.common.docker.addons import (
    remove_container_if_exists, remove_container
)
from vantage6.node.util import logger_name
from vantage6.node.globals import (
    MAX_CHECK_VPN_ATTEMPTS, NETWORK_CONFIG_IMAGE, VPN_CLIENT_IMAGE,
    FREE_PORT_RANGE, DEFAULT_ALGO_VPN_PORT, ALPINE_IMAGE
)
from vantage6.common.docker.network_manager import NetworkManager
from vantage6.node.docker.docker_base import DockerBaseManager


class VPNManager(DockerBaseManager):
    """
    Setup a VPN client in a Docker container and configure the network so that
    the VPN container can forward traffic to and from algorithm containers.
    """
    log = logging.getLogger(logger_name(__name__))

    def __init__(self, isolated_network_mgr: NetworkManager,
                 node_name: str, vpn_volume_name: str, vpn_subnet: str,
                 alpine_image: Union[str, None] = None,
                 vpn_client_image: Union[str, None] = None,
                 network_config_image: Union[str, None] = None) -> None:
        """
        Initializes a VPN manager instance

        Parameters
        ----------
        isolated_network_mgr: NetworkManager
            An object that manages the node's isolated network
        node_name: str
            The name of the node (from config)
        vpn_volume_name: str
            The name of the volume in which the VPN data resides
        vpn_subnet: str
            The IP mask of the VPN subnet
        alpine_image: str or None
            Name of alternative Alpine image to be used
        """
        super().__init__(isolated_network_mgr)

        self.vpn_client_container_name = f'{APPNAME}-{node_name}-vpn-client'
        self.vpn_volume_name = vpn_volume_name
        self.subnet = vpn_subnet
        self.alpine_image = ALPINE_IMAGE if not alpine_image \
            else alpine_image
        self.vpn_client_image = VPN_CLIENT_IMAGE if not vpn_client_image else \
            vpn_client_image
        self.network_config_image = NETWORK_CONFIG_IMAGE \
            if not network_config_image else network_config_image

        self.log.debug('Used VPN images:')
        self.log.debug(f'  Alpine: {self.alpine_image}')
        self.log.debug(f'  Client: {self.vpn_client_image}')
        self.log.debug(f'  Config: {self.network_config_image}')

        self.has_vpn = False

    def connect_vpn(self) -> None:
        """
        Start VPN client container and configure network to allow
        algorithm-to-algoritm communication
        """
        if not self.subnet:
            self.log.warn("VPN subnet is not defined! Disabling VPN...")
            self.log.info("Define the 'vpn_subnet' field in your configuration"
                          " if you want to use VPN")
            return
        elif not self._is_ipv4_subnet(self.subnet):
            self.log.error(f"VPN subnet {self.subnet} is not a valid subnet! "
                           "Disabling VPN...")
            return

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
        remove_container_if_exists(
            docker_client=self.docker, name=self.vpn_client_container_name
        )

        # start vpnclient
        self.log.debug("Starting VPN client container")
        self.vpn_client_container = self.docker.containers.run(
            image=self.vpn_client_image,
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

        # check successful initiation of VPN connection
        if self.has_connection():
            self.log.info("VPN client container was successfully started!")
        else:
            raise ConnectionError("VPN connection not established!")

        # create network exception so that packet transfer between VPN network
        # and the vpn client container is allowed
        self.isolated_bridge = self._find_isolated_bridge()
        if not self.isolated_bridge:
            self.log.error("Setting up VPN failed: could not find bridge "
                           "interface of isolated network")
            return
        self._configure_host_network()

    def has_connection(self) -> bool:
        """ Return True if VPN connection is active """
        self.log.debug("Waiting for VPN connection. This may take a minute...")
        n_attempt = 0
        self.has_vpn = False
        while n_attempt < MAX_CHECK_VPN_ATTEMPTS:
            n_attempt += 1
            try:
                _, vpn_interface = self.vpn_client_container.exec_run(
                    'ip --json addr show dev tun0'
                )
                vpn_interface = json.loads(vpn_interface)
                self.has_vpn = True
                break
            except (JSONDecodeError, docker.errors.APIError):
                # JSONDecodeError if VPN is not setup yet, APIError if VPN
                # container is restarting (e.g. due to connection errors)
                time.sleep(1)
        return self.has_vpn

    def exit_vpn(self) -> None:
        """
        Gracefully shutdown the VPN and clean up
        """
        if not self.has_vpn:
            return
        self.has_vpn = False
        self.log.debug("Stopping and removing the VPN client container")
        remove_container(self.vpn_client_container, kill=True)

        # Clean up host network changes. We have added two rules to the front
        # of the DOCKER-USER chain. We now execute more or less the same
        # commands, but with -D (delete) instead of -I (insert)
        command = (
            'sh -c "'
            f'iptables -D DOCKER-USER -d {self.subnet} '
            f'-i {self.isolated_bridge} -j ACCEPT; '
            f'iptables -D DOCKER-USER -s {self.subnet} '
            f'-o {self.isolated_bridge} -j ACCEPT; '
            '"'
        )
        self.docker.containers.run(
            image=self.network_config_image,
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
        try:
            _, vpn_interface = self.vpn_client_container.exec_run(
                'ip --json addr show dev tun0'
            )
            vpn_interface = json.loads(vpn_interface)
        except (JSONDecodeError, docker.errors.APIError):
            # JSONDecodeError if VPN is not setup yet, APIError if VPN
            # container is restarting (e.g. due to connection errors)
            raise ConnectionError(
                "Could not get VPN IP: VPN is not connected!")
        return vpn_interface[0]['addr_info'][0]['local']

    def forward_vpn_traffic(self, helper_container: Container,
                            algo_image_name: str) -> List[Dict]:
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
        List[Dict] or None
            Description of each port on the VPN client that forwards traffic to
            the algo container. None if VPN is not set up.
        """
        ports = self._forward_traffic_to_algorithm(
            helper_container, algo_image_name)
        self._forward_traffic_from_algorithm(helper_container)
        return ports

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
            image=self.alpine_image,
            network=network,
            cap_add='NET_ADMIN',
            command=cmd,
            remove=True
        )

    def _forward_traffic_to_algorithm(self, algo_helper_container: Container,
                                      algo_image_name: str) -> List[Dict]:
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
        List[Dict] or None
            Description of each port on the VPN client that forwards traffic to
            the algo container. None if VPN is not set up.
        """
        if not self.has_vpn:
            return None  # no port assigned if no VPN is available

        # Get IP Address of the algorithm container
        algo_helper_container.reload()  # update attributes
        algo_ip = self.get_isolated_netw_ip(algo_helper_container)

        # Set ports at which algorithm containers receive traffic
        ports = self._find_exposed_ports(algo_image_name)

        # Find ports on VPN container that are already occupied
        cmd = (
            'sh -c '
            '"iptables -t nat -L PREROUTING | awk \'{print $7}\' | cut -c 5-"'
        )
        occupied_ports = self.vpn_client_container.exec_run(cmd=cmd)
        occupied_ports = occupied_ports.output.decode('utf-8')
        occupied_ports = occupied_ports.split('\n')
        occupied_ports = \
            [int(port) for port in occupied_ports if port != '']

        # take first available port
        vpn_client_port_options = set(FREE_PORT_RANGE) - set(occupied_ports)
        for port in ports:
            port['port'] = vpn_client_port_options.pop()

        # Set up forwarding VPN traffic to algorithm container
        command = 'sh -c "'
        for port in ports:
            command += (
                'iptables -t nat -A PREROUTING -i tun0 -p tcp '
                f'--dport {port["port"]} -j DNAT '
                f'--to {algo_ip}:{port["algo_port"]};'
            )
            # remove the algorithm ports from the dictionaries as these are no
            # longer necessary
            del port['algo_port']
        command += '"'
        self.vpn_client_container.exec_run(command)

        return ports

    def _find_exposed_ports(self, image: str) -> List[Dict]:
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
        List[Dict]:
            List of ports forward VPN traffic to. For each port, a dictionary
            containing port number and label is given
        """
        n2n_image = self.docker.images.get(image)
        default_ports = [{'algo_port': DEFAULT_ALGO_VPN_PORT, 'label': None}]

        exposed_ports = []
        try:
            exposed_ports = n2n_image.attrs['Config']['ExposedPorts']
        except KeyError:
            return default_ports

        # find any labels defined in the docker image
        labels = {}
        try:
            labels = n2n_image.attrs['Config']['Labels']
        except KeyError:
            pass  # No labels found, ignore

        ports = []
        for port in exposed_ports:
            port = port[0:port.find('/')]
            try:
                int(port)
            except ValueError:
                self.log.warn("Could not parse port specified in algorithm "
                              f"docker image {image}: {port}")
            # get port label: this should be defined as 'p1234' for port 1234
            label = None
            if labels:
                label = labels.get('p' + port)
            if not label:
                self.log.warn(f"No label defined in image for port {port}. "
                              "Algorithm will not be able to find the port "
                              "using the label!")
            ports.append({'algo_port': port, 'label': label})

        if not ports:
            self.log.warn(
                "None of the ports in the algorithm image could be parsed. "
                f"Using default port {DEFAULT_ALGO_VPN_PORT} instead")

        return ports if ports else default_ports

    def _find_isolated_bridge(self) -> str:
        """
        Retrieve the linked network interface in the host namespace for
        network interface eth0 in the container namespace.

        Returns
        -------
        string
            The name of the network interface in the host namespace
        """
        # Get the isolated network interface and extract its link index
        isolated_interface = self._get_isolated_interface()
        if isolated_interface:
            link_index = self._get_link_index(isolated_interface)
        else:
            return None  # cannot setup host rules if link is not found

        # Get network config from host namespace
        host_interfaces = self.docker.containers.run(
            image=self.network_config_image,
            network='host',
            command=['ip', '--json', 'addr'],
            remove=True
        )
        host_interfaces = json.loads(host_interfaces)

        linked_interface = self._get_if(host_interfaces, link_index)
        bridge_interface = linked_interface['master']
        return bridge_interface

    def _get_isolated_interface(self):
        """
        Get the isolated network interface

        Get all network descriptions from ip addr and match the isolated
        network's interface by VPN ip address: this should be the same in the
        VPN container's attributes and in the network interface
        """
        isolated_interface = None
        _, interfaces = self.vpn_client_container.exec_run("ip --json addr")
        interfaces = json.loads(interfaces)
        vpn_ip_isolated_netw = self.get_isolated_netw_ip(
            self.vpn_client_container)
        for ip_interface in interfaces:
            if self.is_isolated_interface(ip_interface, vpn_ip_isolated_netw):
                isolated_interface = ip_interface
        return isolated_interface

    def is_isolated_interface(self, ip_interface: Dict,
                              vpn_ip_isolated_netw: str):
        """
        Return True if a network interface is the isolated network
        interface. Identify this based on the IP address of the VPN client in
        the isolated network

        Parameters
        ----------
        ip_interface: dict
            IP interface obtained by executing `ip --json addr` command
        vpn_ip_isolated_netw: str
            IP address of VPN container in isolated network

        Returns
        -------
        boolean:
            True if this is the interface describing the isolated network
        """
        # check if attributes exist in json: if not then it is not the right
        # interface
        if ('addr_info' in ip_interface and len(ip_interface['addr_info']) and
                'local' in ip_interface['addr_info'][0]):
            # Right attributes are present: check if IP addresses match
            return vpn_ip_isolated_netw == \
                ip_interface['addr_info'][0]['local']
        else:
            return False

    def _configure_host_network(self) -> None:
        """
        By default the internal bridge networks are configured to prohibit
        packet forwarding between networks. Create an exception to this rule
        for forwarding traffic between the bridge and vpn network.
        """
        self.log.debug("Configuring host network exceptions for VPN")
        # The following command inserts rules that traffic from the VPN subnet
        # will be accepted into the isolated network
        command = (
            'sh -c "'
            f'iptables -I DOCKER-USER 1 -d {self.subnet} '
            f'-i {self.isolated_bridge} -j ACCEPT; '
            f'iptables -I DOCKER-USER 1 -s {self.subnet} '
            f'-o {self.isolated_bridge} -j ACCEPT; '
            '"'
        )

        self.docker.containers.run(
            image=self.network_config_image,
            network='host',
            cap_add='NET_ADMIN',
            command=command,
            remove=True,
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

    def _is_ipv4_subnet(self, subnet: str) -> bool:
        """
        Validate if subnet has format '12.34.56.78/16'
        """
        parts = subnet.split('/')
        if len(parts) != 2:
            return False
        if not parts[1].isdigit() or int(parts[1]) > 32:
            return False
        octets = parts[0].split(".")
        return len(octets) == 4 and \
            all(o.isdigit() and 0 <= int(o) < 256 for o in octets)
