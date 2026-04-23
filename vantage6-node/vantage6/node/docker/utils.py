import logging

import docker

from vantage6.common import logger_name

log = logging.getLogger(logger_name(__name__))


def login_to_registries(
    registries: list, docker_client: docker.DockerClient | None = None
) -> docker.DockerClient:
    """
    Login to docker registries.

    This is a module-level function so it can be called early in node
    initialization, before DockerManager is instantiated.

    Parameters
    ----------
    registries : list
        List of registry dicts with 'username', 'password', 'registry' keys
    docker_client : docker.DockerClient | None
        Docker client to use. If None, a new client will be created.

    Returns
    -------
    docker.DockerClient
        The authenticated docker client
    """
    if docker_client is None:
        docker_client = docker.from_env()
    for registry in registries:
        try:
            docker_client.login(
                username=registry.get("username"),
                password=registry.get("password"),
                registry=registry.get("registry"),
            )
            log.info(f"Logged in to {registry.get('registry')}")
        except docker.errors.APIError as e:
            log.warning(f"Could not login to {registry.get('registry')}")
            log.warning(e)
    return docker_client
