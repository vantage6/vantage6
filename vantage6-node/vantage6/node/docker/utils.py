import pathlib
import logging

from docker.client import DockerClient
from docker.models.containers import Container

from vantage6.node.util import logger_name

log = logging.getLogger(logger_name(__name__))


def running_in_docker() -> bool:
    """Return True if this code is executed within a Docker container."""
    return pathlib.Path('/.dockerenv').exists()


def get_container(docker_client: DockerClient, **filters) -> Container:
    """
    Return container if it exists after searching using kwargs

    Returns
    -------
    Container or None
        Container if it exists, else None
    """
    running_containers = docker_client.containers.list(
        all=True, filters=filters
    )
    return running_containers[0] if running_containers else None


def remove_container_if_exists(docker_client: DockerClient, **filters) -> None:
    container = get_container(docker_client, **filters)
    if container:
        log.warn("Removing container that was already running: "
                 f"{container.name}")
        remove_container(container, kill=True)


def remove_container(container: Container, kill=False) -> None:
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
        log.error(f"Failed to remove container {container.name}")
        log.debug(e)
