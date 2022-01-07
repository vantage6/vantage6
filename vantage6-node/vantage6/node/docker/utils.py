import pathlib
import logging
import docker

from docker.models.containers import Container

from vantage6.node.util import logger_name

log = logging.getLogger(logger_name(__name__))


def running_in_docker() -> bool:
    """Return True if this code is executed within a Docker container."""
    return pathlib.Path('/.dockerenv').exists()


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
