import docker
import logging

from vantage6.common.docker_addons import remove_container
from vantage6.node.util import logger_name
from vantage6.node.docker.utils import running_in_docker


# TODO maybe move following to utils?
def remove_subnet_mask(ip: str) -> str:
    """
    Remove the subnet mask of an ip address, e.g. 172.1.0.0/16 -> 172.1.0.0
    """
    return ip[0:ip.find('/')]


class IsolatedNetworkManager(object):
    """
    Handle the isolated docker network
    """

    log = logging.getLogger(logger_name(__name__))

    def __init__(self, network_name: str):
        """
        Initialize the IsolatedNetworkManager

        Parameters
        ----------
        network_name: str
            Name of the isolated network
        """
        self.network_name = network_name

        # Connect to docker daemon
        self.docker = docker.from_env()

        # create isolated network
        self.isolated_network = self.create_network()

    def create_network(self) -> docker.models.networks.Network:
        """
        Creates an internal (docker) network

        Used by algorithm containers to communicate with the node API.

        Returns
        -------
        docker.models.networks.Network
            Created docker network
        """
        self.log.debug(
            f"Creating isolated docker-network {self.network_name}!")
        self._delete_existing_network()

        internal_ = running_in_docker()
        if not internal_:
            self.log.warn(
                "Algorithms have internet connection! "
                "This happens because you use 'vnode-local'!"
            )

        network = self.docker.networks.create(
            self.network_name,
            driver="bridge",
            internal=internal_,
            scope="local",
        )
        return network

    def _delete_existing_network(self):
        """ Delete isolated network before creating a new one """
        networks = self.docker.networks.list(
            names=[self.network_name]
        )

        # network = self.docker.networks.get(self.network_name)
        self.log.debug(
            f"Network {self.network_name} already exists. Deleting it.")
        for network in networks:
            # delete any containers that were still attached to the network
            network.reload()
            for container in network.containers:
                self.log.warn(
                    f"Removing container {container.name} in old network")
                remove_container(container, kill=True)
            # then remove the network
            try:
                network.remove()
            except Exception:
                self.log.warn("Could not delete existing isolated network")

    def connect(self, container_name, aliases=None, ipv4=None):
        """Connect to the isolated network."""
        msg = f"Connecting to isolated network '{self.network_name}'"
        self.log.debug(msg)

        # If the network already exists, this is a no-op.
        self.isolated_network.connect(
            container_name, aliases=aliases, ipv4_address=ipv4
        )

    def cleanup(self):
        """Delete the isolated network"""
        try:
            self.isolated_network.remove()
        except Exception as e:
            self.log.error("Could not remove isolated network")
            self.log.error(e)

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
