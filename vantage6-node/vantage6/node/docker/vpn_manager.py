import docker
import logging
import json
import time

from json.decoder import JSONDecodeError
from typing import List, Union, Dict
from docker.models.containers import Container

from vantage6.common.globals import APPNAME
from vantage6.node.util import logger_name
from vantage6.node.globals import (
    MAX_CHECK_VPN_ATTEMPTS, NETWORK_CONFIG_IMAGE, VPN_CLIENT_IMAGE,
    VPN_CONFIG_FILE, VPN_SUBNET, FREE_PORT_RANGE
)
from vantage6.node.docker.network_manager import IsolatedNetworkManager


class VPNManager(object):
    """
    Setup a VPN client in a Docker container and configure the network so that
    the VPN container can forward traffic to and from algorithm containers.
    """
    log = logging.getLogger(logger_name(__name__))

    def __init__(self, isolated_network_mgr: IsolatedNetworkManager,
                 node_name: str):
        self.isolated_network_mgr = isolated_network_mgr
        self.vpn_client_container_name = f'{APPNAME}-{node_name}-vpn-client'

        self.has_vpn = False

        # Connect to docker daemon
        self.docker = docker.from_env()

    def connect_vpn(self, ovpn_file: str) -> None:
        """
        Start VPN client container and configure network to allow
        algorithm-to-algoritm communication

        Parameters
        ----------
        ovpn_file: str
            File location of the OVPN config file
        """
        # define mounting of OVPN config file
        volumes = {ovpn_file: {'bind': '/' + VPN_CONFIG_FILE, 'mode': 'rw'}}
        # set environment variables
        env = {'VPN_CONFIG': '/' + VPN_CONFIG_FILE}

        # start vpnclient
        self.vpn_client_container = self.docker.containers.run(
            image=VPN_CLIENT_IMAGE,
            command="",  # commands to run are already defined in docker image
            volumes=volumes,
            detach=True,
            environment=env,
            name=self.vpn_client_container_name,
            cap_add=['NET_ADMIN', 'SYSLOG'],
            devices=['/dev/net/tun'],
        )

        # attach vpnclient to isolated network
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

    def exit_vpn(self) -> None:
        """
        Gracefully shutdown the VPN and clean up
        """
        if not self.has_vpn:
            return
        self.has_vpn = False
        self.log.debug("Stopping and removing the VPN client container")
        self.vpn_client_container.kill()
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
            except JSONDecodeError:
                time.sleep(1)
        return vpn_interface[0]['addr_info'][0]['local']

    def forward_vpn_traffic(self, algo_container: Container) -> int:
        vpn_port = self._forward_traffic_to_algorithm(algo_container)
        self._forward_traffic_from_algorithm(algo_container)
        return vpn_port

    def _forward_traffic_from_algorithm(
            self, algo_container: Container) -> None:
        """
        Direct outgoing algorithm container traffic to the VPN client container

        Parameters
        ----------
        algo_container: docker.models.containers.Container
            Docker algorithm container
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

        network = 'container:' + algo_container.id

        # add IP route line to the algorithm container network
        cmd = f"ip route replace default via {vpn_local_ip}"
        self.docker.containers.run(
            image='alpine',
            network=network,
            cap_add='NET_ADMIN',
            command=cmd,
            remove=True
        )

    def _forward_traffic_to_algorithm(self, algo_container: Container) -> int:
        """
        Forward incoming traffic from the VPN client container to the
        algorithm container

        Parameters
        ----------
        algo_ip: str
            IP address of the algorithm container in the isolated network

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
        algo_container.reload()  # update attributes
        algo_ip = (
            algo_container.attrs['NetworkSettings']['Networks']
                                [self.isolated_network_mgr.network_name]
                                ['IPAddress']
        )
        # Set port at which algorithm containers receive traffic
        # TODO obtain this port from the Dockerfile description (EXPOSE)
        algorithm_port = '8888'

        # Set up forwarding VPN traffic to algorithm container
        command = (
            'sh -c '
            '"iptables -t nat -A PREROUTING -i tun0 -p tcp '
            f'--dport {vpn_client_port} -j DNAT '
            f'--to {algo_ip}:{algorithm_port}"'
        )
        self.vpn_client_container.exec_run(command)
        return vpn_client_port

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
            f'iptables -I DOCKER-USER 1 -d {VPN_SUBNET} -i {isolated_bridge} '
            '-j ACCEPT; '
            f'iptables -I DOCKER-USER 1 -s {VPN_SUBNET} -o {isolated_bridge} '
            '-j ACCEPT; '
            '"'
        )

        self.docker.containers.run(
            image=NETWORK_CONFIG_IMAGE,
            network='host',
            cap_add='NET_ADMIN',
            command=command,
            auto_remove=True,
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
