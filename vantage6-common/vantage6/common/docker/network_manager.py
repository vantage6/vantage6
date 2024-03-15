import docker
import logging

from docker.models.containers import Container

from vantage6.common.docker.addons import delete_network
from vantage6.common import logger_name


# TODO maybe move following to utils?
def remove_subnet_mask(ip: str) -> str:
    """
    Remove the subnet mask of an ip address, e.g. 172.1.0.0/16 -> 172.1.0.0

    Parameters
    ----------
    ip: str
        IP subnet, potentially including a mask

    Returns
    -------
    str
        IP subnet address without the subnet mask
    """
    return ip[0 : ip.find("/")]


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

    def create_network(self, is_internal: bool = True) -> None:
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

        existing_networks = self.docker.networks.list(names=[self.network_name])
        if existing_networks:
            if len(existing_networks) > 1:
                self.log.error(
                    f"Found multiple ({len(existing_networks)}) existing "
                    f"networks {self.network_name}. Please delete all or all "
                    "but one before starting the server!"
                )
                exit(1)
            self.log.info(
                f"Network {self.network_name} already exists! Using " "existing network"
            )
            self.network = existing_networks[0]
            self.network.reload()  # required to initialize containers in netw
        else:
            self.network = self.docker.networks.create(
                self.network_name,
                driver="bridge",
                internal=is_internal,
                scope="local",
            )

    def delete(self, kill_containers: bool = True) -> None:
        """
        Delete network

        Parameters
        ----------
        kill_containers: bool
            If true, kill and remove any containers in the network
        """
        networks = self.docker.networks.list(names=[self.network_name])

        self.log.debug("Deleting network %s.", self.network_name)
        for network in networks:
            delete_network(network, kill_containers)

    def contains(self, container: Container) -> bool:
        """
        Whether or not this network contains a certain container

        Parameters
        ----------
        container: Container
            container to look for in network

        Returns
        -------
        bool
            Whether or not container is in the network
        """
        self.network.reload()
        return container in self.network.containers

    def connect(
        self, container_name: str, aliases: list[str] = None, ipv4: str | None = None
    ) -> None:
        """
        Connect a container to the network.

        Parameters
        ----------
        container_name: str
            Name of the container that should be connected to the network
        aliases: list[str]
            A list of aliases for the container in the network
        ipv4: str | None
            An IP address to assign to the container in the network
        """
        self.log.debug(f"Connecting {container_name} to network '{self.network_name}'")
        self.network.connect(container_name, aliases=aliases, ipv4_address=ipv4)

    def disconnect(self, container_name: str) -> None:
        """
        Disconnect a container from the network.

        Parameters
        ----------
        container:
            Name of the container to disconnect
        """
        self.log.debug(
            f"Disconnecting {container_name} from network" f"'{self.network_name}'"
        )
        self.network.disconnect(container=container_name, force=True)

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
        containers = self.network.attrs["Containers"]
        for container_id, container_dict in containers.items():
            if container_dict["Name"] == container_name:
                ip = container_dict["IPv4Address"]
        if not ip:
            self.log.warn(
                f"IP Address for container {container_name} not " "found in the network"
            )
            return None
        ip = remove_subnet_mask(ip)
        return ip
