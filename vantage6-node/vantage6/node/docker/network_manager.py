import docker
import ipaddress
import logging

from vantage6.node.globals import LOCAL_SUBNET_START
from vantage6.node.util import logger_name
from vantage6.node.docker.utils import running_in_docker


# TODO maybe move following to utils?
def remove_subnet_mask(ip):
    return ip[0:ip.find('/')]


class IsolatedNetworkManager(object):

    log = logging.getLogger(logger_name(__name__))

    def __init__(self, network_name):
        self.network_name = network_name

        # Connect to docker daemon
        self.docker = docker.from_env()

        # create isolated network
        self.isolated_network = self.create_network()

    def create_network(self) -> docker.models.networks.Network:
        """
        Creates an internal (docker) network

        Used by algorithm containers to communicate with the node API.

        Parameters
        ----------
        network_name: str
            Name of the network to be created

        Returns
        -------
        docker.models.networks.Network
            Created docker network
        """
        try:
            network = self.docker.networks.get(self.network_name)
            self.log.debug(
                f"Network {self.network_name} already exists. Deleting it.")
            network.remove()
        except Exception:
            self.log.debug("No network found...")

        self.log.debug(
            f"Creating isolated docker-network {self.network_name}!")

        internal_ = running_in_docker()
        if not internal_:
            self.log.warn(
                "Algorithms have internet connection! "
                "This happens because you use 'vnode-local'!"
            )

        # define configuration for the subnet in which the network is created
        subnet = self._get_available_subnet()
        gateway = str(ipaddress.ip_address(remove_subnet_mask(subnet)) + 1)
        ipam_pool = docker.types.IPAMPool(subnet=subnet, gateway=gateway)
        ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])

        network = self.docker.networks.create(
            self.network_name,
            driver="bridge",
            internal=internal_,
            scope="local",
            ipam=ipam_config
        )
        return network

    def connect(self, container_name, aliases=None, ipv4=None):
        """Connect to the isolated network."""
        msg = f"Connecting to isolated network '{self.network_name}'"
        self.log.debug(msg)

        # If the network already exists, this is a no-op.
        self.isolated_network.connect(
            container_name, aliases=aliases, ipv4_address=ipv4
        )

    def get_available_ip(self) -> str:
        """
        Get a non-used IP address in the isolated network

        Returns
        -------
        str
            IP address in isolated network
        """
        # ensure isolated network attributes are updated
        self.isolated_network.reload()

        # get subnet of isolated network
        subnet = ipaddress.ip_network(
            self.isolated_network.attrs['IPAM']['Config'][0]['Subnet']
        )

        # get occupied IP addresses
        containers_info = self.isolated_network.attrs['Containers'].items()
        occupied_ips = []
        for container_id, container_info in containers_info:
            occupied_ips.append(ipaddress.ip_address(
                remove_subnet_mask(container_info['IPv4Address'])
            ))
        occupied_ips = sorted(occupied_ips)
        max_occupied_ip = occupied_ips[-1] if occupied_ips \
            else ipaddress.ip_address(
                self.isolated_network.attrs['IPAM']['Config'][0]['Gateway']
            )

        # increment IP address (as this is IPv4Address object this works)
        new_ip = max_occupied_ip + 1

        # check that the new IP address is within the subnet
        if new_ip not in subnet:
            self.log.error("No IP addresses available within the isolated "
                           "network")
            self.log.error("Turning off VPN")
            return None

        return new_ip

    def get_container_ip(self, container_name: str) -> str:
        """
        Get IP address of the VPN client in the isolated network

        Returns
        -------
        str
            IP address of VPN client container in the isolated network
        """
        self.isolated_network.reload()
        ip = None
        isol_net_containers = self.isolated_network.attrs['Containers']
        for container_id, container_dict in isol_net_containers.items():
            if container_dict['Name'] == container_name:
                ip = container_dict['IPv4Address']
        if not ip:
            self.log.warn(
                f"IP Address for container {container_name} not found in the "
                "isolated network"
            )
            return None
        ip = remove_subnet_mask(ip)
        return ip

    def _get_available_subnet(self) -> str:
        """
        Get a subnet to be used for isolated network that is not occupied on
        the host

        Returns
        ------
        str
            Subnet to be used for isolated network
        """
        # find which subnets are already taken by other docker networks
        occupied_subnets = []
        for network in self.docker.networks.list():
            config = network.attrs['IPAM']['Config']
            if len(config) and "Subnet" in config[0]:
                occupied_subnets.append(
                    ipaddress.ip_network(config[0]['Subnet'])
                )
        # for all docker other docker nets, extract the second octet
        occupied_subnets = [
            int(str(s).split('.')[1]) for s in occupied_subnets
            if str(s).startswith(LOCAL_SUBNET_START)
        ]

        # select a second octet for the new subnet
        second_octet_options = set(range(1, 256)) - set(occupied_subnets)
        second_octet_new = next(iter(second_octet_options))
        return LOCAL_SUBNET_START + str(second_octet_new) + '.0.0/16'
