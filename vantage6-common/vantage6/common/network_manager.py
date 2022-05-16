from typing import List, Union
import docker
import logging

from vantage6.common.docker_addons import remove_container
from vantage6.common import logger_name


# TODO maybe move following to utils?
def remove_subnet_mask(ip: str) -> str:
    """
    Remove the subnet mask of an ip address, e.g. 172.1.0.0/16 -> 172.1.0.0
    """
    return ip[0:ip.find('/')]


class NetworkManager(object):
    """
    Handle a Docker network
    """

    log = logging.getLogger(logger_name(__name__))

    def __init__(self, network_name: str):
        """
        Initialize the NetworkManager

        Parameters
        ----------
        network_name: str
            Name of the network
        """
        self.network_name = network_name
        self.network = None

        # Connect to docker daemon
        self.docker = docker.from_env()

    def create_network(
        self, is_internal: bool = True
    ) -> None:
        """
        Creates an internal (docker) network

        Used by algorithm containers to communicate with the node API.

        Parameters
        ----------
        is_internal: bool
            True if network should only be able to communicate internally
        """
        if self.network:
            self.log.warn(f"Network {self.network_name} was already created!")
            return

        self.log.debug(
            f"Creating Docker network {self.network_name}!")
        # Delete network if it already exists
        self.delete()

        self.network = self.docker.networks.create(
            self.network_name,
            driver="bridge",
            internal=is_internal,
            scope="local",
        )

    def delete(self, kill_containers: bool = True) -> None:
        """ Delete network

        Parameters
        ----------
        kill_containers: bool
            If true, kill and remove any containers in the network
        """
        networks = self.docker.networks.list(
            names=[self.network_name]
        )

        # network = self.docker.networks.get(self.network_name)
        self.log.debug(
            f"Network {self.network_name} already exists. Deleting it.")
        for network in networks:
            if kill_containers:
                # delete any containers that were still attached to the network
                network.reload()
                for container in network.containers:
                    self.log.warn(
                        f"Removing container {container.name} in old network")
                    remove_container(container, kill=True)
            # remove the network
            try:
                network.remove()
            except Exception:
                self.log.warn(
                    f"Could not delete existing network {self.network_name}")

    def connect(self, container_name: str, aliases: List[str] = [],
                ipv4: Union[str, None] = None) -> None:
        """
        Connect a container to the network.

        Parameters
        ----------
        container_name: str
            Name of the container that should be connected to the network
        aliases: List[str]
            A list of aliases for the container in the network
        ipv4: str
            An IP address to assign to the container in the network
        """
        self.log.debug(
            f"Connecting {container_name} to network '{self.network_name}'")
        self.network.connect(
            container_name, aliases=aliases, ipv4_address=ipv4
        )

    def get_container_ip(self, container_name: str) -> str:
        """
        Get IP address of a container in the network

        Parameters
        ----------
        container_name: str
            Name of the container whose IP address is sought

        Returns
        -------
        str
            IP address of the container in the network
        """
        self.network.reload()
        ip = None
        containers = self.network.attrs['Containers']
        for container_id, container_dict in containers.items():
            if container_dict['Name'] == container_name:
                ip = container_dict['IPv4Address']
        if not ip:
            self.log.warn(f"IP Address for container {container_name} not "
                          "found in the network")
            return None
        ip = remove_subnet_mask(ip)
        return ip
