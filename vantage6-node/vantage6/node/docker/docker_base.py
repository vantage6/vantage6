import docker

from vantage6.common.docker.network_manager import NetworkManager


class DockerBaseManager(object):
    """
    Base class for docker-using classes. Contains simple methods that are used
    by multiple derived classes
    """
    def __init__(self, isolated_network_mgr: NetworkManager) -> None:
        self.isolated_network_mgr = isolated_network_mgr

        # Connect to docker daemon
        self.docker = docker.from_env()

    def get_isolated_netw_ip(self, container) -> str:
        """
        Get address of a container in the isolated network

        Parameters
        ----------
        container: Container
            Docker container whose IP address should be obtained

        Returns
        -------
        str
            IP address of a container in isolated network
        """
        container.reload()
        return container.attrs[
            'NetworkSettings'
        ]['Networks'][self.isolated_network_mgr.network_name]['IPAddress']
