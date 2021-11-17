import docker

from docker.models.containers import Container

from vantage6.node.docker.network_manager import IsolatedNetworkManager


class DockerBaseManager(object):
    """
    Base class for docker-using classes. Contains simple methods that are used
    by multiple derived classes
    """
    def __init__(self, isolated_network_mgr: IsolatedNetworkManager) -> None:
        self.isolated_network_mgr = isolated_network_mgr

        # Connect to docker daemon
        self.docker = docker.from_env()

    def get_container(self, **filters) -> Container:
        """
        Return container if it exists after searching using kwargs

        Returns
        -------
        Container or None
            Container if it exists, else None
        """
        running_containers = self.docker.containers.list(
            all=True, filters=filters
        )
        return running_containers[0] if running_containers else None

    def remove_container(self, container: Container, kill=False) -> None:
        """
        Removes a docker container

        Parameters
        ----------
        container: Container
            The container that should be removed
        kill: bool
            Whether or not container should be killed before it is removed
        """
        if kill:
            try:
                container.kill()
            except Exception as e:
                pass  # allow failure here, maybe container had already exited
        try:
            container.remove()
        except Exception as e:
            self.log.error(f"Failed to remove container {container.name}")
            self.log.debug(e)

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
