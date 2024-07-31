import logging
import signal
import pathlib

import docker
from docker.client import DockerClient
from docker.models.containers import Container
from docker.models.volumes import Volume
from docker.models.networks import Network
from docker.utils import parse_repository_tag
from docker.auth import resolve_repository_name

from vantage6.common import logger_name
from vantage6.common.globals import APPNAME

log = logging.getLogger(logger_name(__name__))


class ContainerKillListener:
    """Listen for signals that the docker container should be shut down"""

    kill_now = False

    def __init__(self) -> None:
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    # pylint: disable=unused-argument
    def exit_gracefully(self, *args) -> None:
        """Set kill_now to True. This will trigger the container to stop"""
        self.kill_now = True


def check_docker_running() -> None:
    """
    Check if docker engine is running. If not, exit the program.
    """
    try:
        docker_client = docker.from_env()
        docker_client.ping()
    except Exception as exc:
        log.error("Cannot reach the Docker engine! Please make sure Docker is running.")
        log.exception(exc)
        log.warning("Exiting...")
        exit(1)


def running_in_docker() -> bool:
    """
    Check if this code is executed within a Docker container.

    Returns
    -------
    bool
        True if the code is executed within a Docker container, False otherwise
    """
    return pathlib.Path("/.dockerenv").exists()


def pull_image(
    docker_client: DockerClient, image: str, suppress_error: bool = False
) -> None:
    """
    Pull a docker image

    Parameters
    ----------
    docker_client: DockerClient
        A Docker client
    image: str
        Name of the image to pull
    suppress_error: bool
        Whether to suppress the error if the image could not be pulled

    Raises
    ------
    docker.errors.APIError
        If the image could not be pulled
    """
    try:
        docker_client.images.pull(image)
        log.debug("Succeeded to pull image %s", image)
    except docker.errors.APIError as exc:
        if not suppress_error:
            log.error("Failed to pull image! %s", image)
            log.exception(exc)
        raise docker.errors.APIError("Failed to pull image") from exc


def get_container(docker_client: DockerClient, **filters) -> Container:
    """
    Return container if it exists after searching using kwargs

    Parameters
    ----------
    docker_client: DockerClient
        Python docker client
    **filters:
        These are arguments that will be passed to the client.container.list()
        function. They should yield 0 or 1 containers as result (e.g.
        name='something')

    Returns
    -------
    Container or None
        Container if it exists, else None
    """
    running_containers = docker_client.containers.list(all=True, filters=filters)
    return running_containers[0] if running_containers else None


def remove_container_if_exists(docker_client: DockerClient, **filters) -> None:
    """
    Kill and remove a docker container if it exists

    Parameters
    ----------
    docker_client: DockerClient
        A Docker client
    **filters:
        These are arguments that will be passed to the client.container.list()
        function. They should yield 0 or 1 containers as result (e.g.
        name='something')
    """
    container = get_container(docker_client, **filters)
    if container:
        log.warning("Removing container that was already running: %s", container.name)
        remove_container(container, kill=True)


def remove_container(container: Container, kill: bool = False) -> None:
    """
    Removes a docker container

    Parameters
    ----------
    container: Container
        The container that should be removed
    kill: bool
        Whether or not container should be killed before it is removed
    """
    try:
        container.remove(force=kill)
    except Exception as e:
        log.exception("Failed to remove container %s", container.name)
        log.exception(e)


def stop_container(container: Container, force: bool = False):
    """
    Stop a docker container

    Parameters
    ----------
    container: Container
        The container that should be stopped
    force: bool
        Whether to kill the container or if not, try to stop it gently
    """
    if force:
        container.kill()
    else:
        container.stop()


def get_network(docker_client: DockerClient, **filters) -> Network:
    """Return network if it exists after searching using kwargs

    Parameters
    ----------
    docker_client: DockerClient
        Python docker client
    **filters:
        These are arguments that will be passed to the client.network.list()
        function. They should yield 0 or 1 networks as result (e.g.
        name='something')

    Returns
    -------
    Container or None
        Container if it exists, else None
    """
    networks = docker_client.networks.list(filters=filters)
    return networks[0] if networks else None


def delete_network(network: Network | None, kill_containers: bool = True) -> None:
    """Delete network and optionally its containers

    Parameters
    ----------
    network: Network | None
        Network to delete
    kill_containers: bool
        Whether to kill the containers in the network (otherwise they are
        merely disconnected)
    """
    if not network:
        log.warning("Network not defined! Not removing anything, continuing...")
        return
    network.reload()
    for container in network.containers:
        log.info("Removing container %s in old network", container.name)
        if kill_containers:
            log.warning("Killing container %s", container.name)
            remove_container(container, kill=True)
        else:
            network.disconnect(container)
    # remove the network
    try:
        network.remove()
    except docker.errors.APIError:
        log.warning("Could not delete existing network %s", network.name)


def get_networks_of_container(container: Container) -> dict:
    """
    Get list of networks the container is in

    Parameters
    ----------
    container: Container
        The container in which we are interested

    Returns
    -------
    dict
        Describes container's networks and their properties
    """
    container.reload()
    return container.attrs["NetworkSettings"]["Networks"]


def get_num_nonempty_networks(container: Container) -> int:
    """
    Get number of networks the container is in where it is not the only one

    Parameters
    ----------
    container: Container
        The container in which we are interested

    Returns
    -------
    int
        Number of networks in which the container resides in which there are
        also other containers
    """
    count_non_empty_networks = 0
    docker_client = docker.from_env()

    networks = get_networks_of_container(container)
    for network_properties in networks.values():
        network_obj = docker_client.networks.get(network_properties["NetworkID"])
        if not network_obj:
            continue
        containers = network_obj.attrs["Containers"]
        if len(containers) > 1:
            count_non_empty_networks += 1
    return count_non_empty_networks


def get_server_config_name(container_name: str, scope: str) -> str:
    """
    Get the configuration name of a server from its docker container name

    Docker container name of the server is formatted as
    f"{APPNAME}-{self.name}-{self.scope}-server". This will return {self.name}

    Parameters
    ----------
    container_name: str
        Name of the docker container in which the server is running
    scope: str
        Scope of the server (e.g. 'system' or 'user')

    Returns
    -------
    str
        A server's configuration name
    """
    idx_scope = container_name.rfind(scope)
    length_app_name = len(APPNAME)
    return container_name[length_app_name + 1 : idx_scope - 1]


def delete_volume_if_exists(client: docker.DockerClient, volume_name: Volume) -> None:
    """
    Delete a volume if it exists

    Parameters
    ----------
    client: docker.DockerClient
        Docker client
    volume: Volume
        Volume to delete
    """
    try:
        volume = client.volumes.get(volume_name)
        if volume:
            volume.remove()
    except (docker.errors.NotFound, docker.errors.APIError):
        log.warning("Could not delete volume %s", volume_name)


def parse_image_name(image: str) -> tuple[str, str, str]:
    """
    Parse image name into registry, repository, tag.

    The returned tag may also be a digest. If image contains both a tag and a digest,
    the digest will be returned rather than the tag.

    Parameters
    ----------
    image: str
        Image name. E.g. "harbor2.vantage6.ai/algorithms/average:latest" or
        "library/hello-world"

    Returns
    -------
    tuple[str, str, str]
        Registry, repository, and tag. Tag is "latest" if not specified in 'image'
    """
    registry_repository, tag = parse_repository_tag(image)
    tag = tag or "latest"
    if tag.startswith("sha256:"):
        # If the tag is a digest, the repository may include another tag, e.g. if
        # the image is "some-image:test@sha256:1234", the registry_repository would
        # still include the tag "test". If this is the case, set that as the tag,
        # because the tag is more reliable for policies than the digest (see
        # e.g. https://github.com/vantage6/vantage6/pull/1318#discussion_r1685560071)
        registry_repository, tag_ = parse_repository_tag(registry_repository)
        if tag_:
            tag = tag_
    registry, repository = resolve_repository_name(registry_repository)
    return registry, repository, tag


def get_image_name_wo_tag(image: str) -> str:
    """
    Get image name without tag

    Parameters
    ----------
    image: str
        Image name. E.g. "harbor2.vantage6.ai/algorithms/average:latest"

    Returns
    -------
    str
        Image name without tag. E.g. "harbor2.vantage6.ai/algorithms/average"
    """
    registry, repository, _ = parse_image_name(image)
    if registry == "docker.io":
        return repository
    else:
        return f"{registry}/{repository}"


def get_digest(
    full_image: str,
    client: DockerClient | None = None,
    docker_username: str | None = None,
    docker_password: str | None = None,
) -> str:
    """
    Get digest of an image

    Parameters
    ----------
    full_image: str
        Image name. E.g. "harbor2.vantage6.ai/algorithms/average:latest"
    client: DockerClient | None
        Docker client to use. If not provided, a new client will be created. An existing
        client could be useful to provide if it has already been authenticated with one
        or more registries
    docker_username: str | None
        Docker username to authenticate with at the registry. Required if the image is
        private
    docker_password: str | None
        Docker password to authenticate with at the registry. Required if the image is
        private

    Returns
    -------
    str | None
        Digest of the image or `None` if the digest could not be found
    """
    if not client:
        client = docker.from_env()
    try:
        if docker_username and docker_password:
            distribution = client.api.inspect_distribution(
                full_image,
                auth_config={"username": docker_username, "password": docker_password},
            )
        else:
            distribution = client.api.inspect_distribution(full_image)
    except docker.errors.APIError:
        log.warning("Could not find distribution specs of image %s", full_image)
        return None

    try:
        return distribution["Descriptor"]["digest"]
    except KeyError:
        log.warning(
            "Distribution spec of image '%s' did not include image digest", full_image
        )
        return None
