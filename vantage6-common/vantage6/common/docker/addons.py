import logging
import signal
import pathlib
import re
import json
import hashlib
from http import HTTPStatus

import requests
from requests.auth import HTTPBasicAuth

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
    the tag will be returned rather than the digest.

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


def get_manifest(
    full_image: str,
    registry_user: str | None = None,
    registry_password: str | None = None,
) -> requests.Response:
    """
    Get the manifest of an image

    This uses the OCI distribution specification which is supported by all major
    container registries.

    Parameters
    ----------
    full_image: str
        Image name. E.g. "harbor2.vantage6.ai/algorithms/average:latest"
    registry_user: str | None
        Docker username to authenticate with at the registry. Required if the image is
        private
    registry_password: str | None
        Docker password to authenticate with at the registry. Required if the image is
        private

    Returns
    -------
    requests.Response
        Response containing the manifest of the image

    Raises
    ------
    ValueError
        If the image name is invalid
    """
    registry, image, tag = parse_image_name(full_image)

    # if requesting from docker hub, manifests are at 'registry-1.docker.io'
    if registry == "docker.io":
        registry = "registry-1.docker.io"

    # request manifest. First try without authentication, as that is the most common
    # case. If that fails, try with authentication
    headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    manifest_endpoint = f"https://{registry}/v2/{image}/manifests/{tag}"
    response = requests.get(manifest_endpoint, headers=headers, timeout=60)

    # try requesting manifest using authentication from 'www-authenticate' header if
    # anonymous request failed. This has been tested with DockerHub and Github container
    # registry
    if (
        response.status_code == HTTPStatus.UNAUTHORIZED
        and "www-authenticate" in response.headers
    ):
        realm_pattern = r'Bearer realm="(?P<realm>[^"]+)"'
        scope_pattern = r'scope="(?P<scope>[^"]+)"'
        service_pattern = r'service="(?P<service>[^"]+)"'
        realm_match = re.match(realm_pattern, response.headers["www-authenticate"])
        scope_match = re.search(scope_pattern, response.headers["www-authenticate"])
        service_match = re.search(service_pattern, response.headers["www-authenticate"])
        if realm_match and scope_match and service_match:
            token_response = requests.get(
                realm_match.group("realm"),
                params={
                    "scope": scope_match.group("scope"),
                    "service": service_match.group("service"),
                },
                timeout=60,
            )
            if token_response.status_code == HTTPStatus.OK:
                token = token_response.json()["token"]
                response = requests.get(
                    manifest_endpoint,
                    headers={"Authorization": f"Bearer {token}", **headers},
                    timeout=60,
                )

    # If still getting unauthorize, try with username and password. The following code
    # was tested with private images on harbor2.vantage6.ai.
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response = requests.get(
            manifest_endpoint,
            headers=headers,
            auth=HTTPBasicAuth(registry_user, registry_password),
            timeout=60,
        )

    # handle errors or return manifest
    if response.status_code == HTTPStatus.NOT_FOUND:
        raise ValueError(f"Image {image}:{tag} from registry {registry} not found!")
    elif response.status_code != HTTPStatus.OK:
        raise ValueError(
            "Could not retrieve image manifest from "
            f"https://{registry}/v2/{image}/manifests/{tag}"
        )
    return response


def _get_digest_via_docker(
    full_image: str,
    client: DockerClient,
    docker_username: str | None = None,
    docker_password: str | None = None,
) -> str:
    """
    Get digest of an image by fetching the distribution specs using the Docker client

    Parameters
    ----------
    full_image: str
        Image name. E.g. "harbor2.vantage6.ai/algorithms/average:latest"
    client: DockerClient
        Docker client.
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


def _get_digest_via_manifest(
    full_image: str,
    docker_username: str | None = None,
    docker_password: str | None = None,
) -> str:
    """
    Get digest of an image by fetching the manifest

    Parameters
    ----------
    full_image: str
        Image name. E.g. "harbor2.vantage6.ai/algorithms/average:latest"
    docker_username: str | None
        Docker username to authenticate with at the registry. Required if the image is
        private
    docker_password: str | None
        Docker password to authenticate with at the registry. Required if the image is
        private

    Returns
    -------
    str
        Digest of the image
    """
    manifest_response = get_manifest(full_image, docker_username, docker_password)
    if "Docker-Content-Digest" in manifest_response.headers:
        return manifest_response.headers["Docker-Content-Digest"]
    else:
        return __calculate_digest(manifest_response.json())


def get_digest(
    full_image: str,
    client: DockerClient | None = None,
    docker_username: str | None = None,
    docker_password: str | None = None,
) -> str:
    """
    Get digest of a Docker image

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
    if client is not None:
        return _get_digest_via_docker(
            full_image, client, docker_username, docker_password
        )
    else:
        return _get_digest_via_manifest(full_image, docker_username, docker_password)


def __calculate_digest(manifest: str) -> str:
    """
    Calculate the SHA256 digest from a Docker image manifest.
    Parameters
    ----------
    manifest : str
        Docker image manifest

    Returns
    -------
    str
        SHA256 digest of the manifest
    """
    # Serialize the manifest using canonical JSON
    serialized_manifest = json.dumps(
        manifest,
        indent=3,  # Believe it or not, this spacing is required to get the right SHA
    ).encode("utf-8")
    # Calculate the SHA256 digest
    digest = hashlib.sha256(serialized_manifest).hexdigest()
    return f"sha256:{digest}"
