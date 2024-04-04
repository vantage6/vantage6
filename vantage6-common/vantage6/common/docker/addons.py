from datetime import datetime
import logging
import re
import docker
import requests
import base64
import json
import signal
import pathlib

from dateutil.parser import parse
from docker.client import DockerClient
from docker.models.containers import Container
from docker.models.volumes import Volume
from docker.models.networks import Network

from vantage6.common import logger_name
from vantage6.common import ClickLogger
from vantage6.common.globals import APPNAME

log = logging.getLogger(logger_name(__name__))


class ContainerKillListener:
    """Listen for signals that the docker container should be shut down"""

    kill_now = False

    def __init__(self) -> None:
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

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
    except Exception as e:
        log.error(
            "Cannot reach the Docker engine! Please make sure Docker " "is running."
        )
        log.warning("Exiting...")
        log.debug(e)
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


def registry_basic_auth_header(
    docker_client: DockerClient, registry: str
) -> dict[str, str]:
    """
    Obtain credentials for registry

    This is a wrapper around docker-py to obtain the credentials used
    to access a registry. Normally communication to the registry goes
    through the Docker deamon API (locally), therefore we have to take
    extra steps in order to communicate with the (Harbor) registry
    directly.

    Note that this has only been tested for the harbor registries.

    Parameters
    ----------
    docker_client: DockerClient
        Docker client
    registry : str
        registry name (e.g. harbor2.vantage6.ai)

    Returns
    -------
    dict
        Containing a basic authorization header
    """

    # Obtain the header used to be send to the docker deamon. We
    # communicate directly with the registry therefore we need to
    # change this headers.
    header = docker.auth.get_config_header(docker_client.api, registry)
    if not header:
        log.debug(f"No credentials found for {registry}")
        return

    # decode header
    header_json = json.loads(base64.b64decode(header))

    # Extract username and password. Depending on the docker version, the keys
    # may be capitalized in the JSON header
    username = (
        header_json["username"]
        if "username" in header_json
        else header_json["Username"]
    )
    password = (
        header_json["password"]
        if "password" in header_json
        else header_json["Password"]
    )
    basic_auth = f"{username}:{password}"

    # Encode them back to base64 and as a dict
    bytes_basic_auth = basic_auth.encode("utf-8")
    b64_basic_auth = base64.b64encode(bytes_basic_auth).decode("utf-8")

    return {"authorization": f"Basic {b64_basic_auth}"}


def inspect_remote_image_timestamp(
    docker_client: DockerClient,
    image: str,
    log: logging.Logger | ClickLogger = ClickLogger,
) -> tuple[datetime, str] | None:
    """
    Obtain creation timestamp object from remote image.

    Parameters
    ----------
    docker_client: DockerClient
        Docker client
    image: str
        Image name
    log: logging.Logger | ClickLogger
        Logger

    Returns
    -------
    tuple[datetime, str] | None
        Timestamp containing the creation date of the image and its digest, or
        None if the remote image could not be found.
    """
    # check if a tag has been provided
    img_split_colon = re.split(":", image)
    img = ":".join(img_split_colon[:-1])
    tag = img_split_colon[-1] if len(img_split_colon) > 1 else "latest"

    img_split_slash = re.split("/", img)
    if len(img_split_slash) > 3:
        # docker registry is part before first slash, repository is everything
        # in between, image is the last part (see
        # https://github.com/goharbor/harbor/issues/3162)
        reg = img_split_slash[0]
        rep = "/".join(img_split_slash[1:-1])
        img_ = img_split_slash[-1]
    elif len(img_split_slash) < 3:
        log.warning(
            "Could not construct remote URL - will try to pull from Docker Hub!"
        )
        return _get_dockerhub_timestamp_digest(img, tag)

    # figure out API version of the docker repo if it is a harbor repo. Harbor
    # registries provide the 'pushed' time which the OCI specification does not, and
    # this is convenient to have.
    v2_check = requests.get(f"https://{reg}/api/v2.0/health")
    if v2_check.status_code == 200:
        return _get_harbor_v2_timestamp_digest(docker_client, reg, rep, img_, tag)
    # TODO: consider dropping harbor v1 support (v2 is available since May 2020)
    v1_check = requests.get(f"https://{reg}/api/health")
    if v1_check.status_code == 200:
        return _get_harbor_v1_timestamp_digest(docker_client, reg, rep, img_, tag)

    # if the registry is not a harbor registry, we will try to get the timestamp
    # and digest using OCI endpoints
    timestamp, digest = _get_generic_timestamp_digest(
        docker_client, reg, rep, img_, tag
    )

    # warning for non-harbor registries
    if not timestamp:
        log.warning(
            "Could not find image info for %s! If you are using a private Docker "
            "such as harbor, please check that it is online.",
            image,
        )

    return timestamp, digest


def _get_generic_timestamp_digest(
    docker_client: DockerClient, reg: str, rep: str, image: str, tag: str
) -> tuple[datetime, str] | None:
    """
    Get creation timestamp object and digest from remote image for generic registry.

    Parameters
    ----------
    docker_client: DockerClient
        Docker client
    reg: str
        Registry name
    rep: str
        Repository name
    image: str
        Image name
    tag: str
        Tag name
    """
    # Use OCI endpoints to get manifest info, which contains the digest
    image_info = f"https://{reg}/v2/{rep}/{image}/manifests/{tag}"
    result = requests.get(
        image_info, headers=registry_basic_auth_header(docker_client, reg)
    )
    # Check that response is OK
    if not _check_response_status(result):
        return None, None
    try:
        digest = result.json().get("config").get("digest")
    except AttributeError:
        log.warning("Could not find digest in the manifest!")
        return None, None

    # Use OCI endpoint to get the creation timestamp using the digest
    image_info = f"https://{reg}/v2/{rep}/{image}/blobs/{digest}"
    result = requests.get(
        image_info, headers=registry_basic_auth_header(docker_client, reg)
    )
    # Check that response is OK
    if not _check_response_status(result):
        return None, digest
    try:
        timestamp = parse(result.json().get("created"))
    except AttributeError:
        log.warning("Could not find creation timestamp!")
        return None, digest

    return timestamp, digest


def _get_dockerhub_timestamp_digest(
    image: str, tag: str
) -> tuple[datetime, str] | None:
    """
    Obtain creation timestamp object and digest from remote image for Docker Hub.

    Parameters
    ----------
    image: str
        Image name
    tag: str
        Tag name

    Returns
    -------
    tuple[datetime, str] | None
        Timestamp containing the creation date of the image and its digest, or
        None if the remote image could not be found.
    """
    image_info = f"https://hub.docker.com/v2/repositories/{image}/tags/{tag}"
    result = requests.get(image_info)
    # Check that response is OK
    if not _check_response_status(result):
        return None, None
    try:
        digest = result.json().get("digest")
        timestamp = parse(result.json().get("last_updated"))
    except AttributeError:
        log.warning("Could not find digest in the manifest!")
        return None, None

    return timestamp, digest


def _get_harbor_v2_timestamp_digest(
    docker_client, registry: str, repository: str, image: str, tag: str
) -> tuple[datetime, str] | None:
    """
    Obtain creation timestamp object and digest from remote image for Harbor v2.

    Parameters
    ----------
    docker_client: DockerClient
        Docker client
    registry: str
        Registry name (e.g. harbor2.vantage6.ai)
    repository: str
        Repository name
    image: str
        Image name
    tag: str
        Tag name

    Returns
    -------
    tuple[datetime, str] | None
        Timestamp containing the creation date of the image and its digest, or
        None if the remote image could not be found.
    """
    image_info = (
        f"https://{registry}/api/v2.0/projects/{repository}/repositories/"
        f"{image}/artifacts/{tag}"
    )

    result = requests.get(
        image_info, headers=registry_basic_auth_header(docker_client, registry)
    )

    # Check that response is OK
    if not _check_response_status(result):
        return None, None

    timestamp = parse(result.json().get("push_time"))
    digest = result.json().get("digest")
    return timestamp, digest


def _get_harbor_v1_timestamp_digest(
    docker_client, registry: str, repository: str, image: str, tag: str
) -> tuple[datetime, str] | None:
    """
    Obtain creation timestamp object and digest from remote image for Harbor v1.

    Parameters
    ----------
    docker_client: DockerClient
        Docker client
    registry: str
        Registry name (e.g. harbor2.vantage6.ai)
    repository: str
        Repository name
    image: str
        Image name
    tag: str
        Tag name

    Returns
    -------
    tuple[datetime, str] | None
        Timestamp containing the creation date of the image and its digest, or
        None if the remote image could not be found.
    """
    image_info = f"https://{registry}/api/repositories/{repository}/{image}/tags/{tag}"

    result = requests.get(
        image_info, headers=registry_basic_auth_header(docker_client, registry)
    )

    # Check that response is OK
    if not _check_response_status(result):
        return None, None

    timestamp = parse(result.json().get("created"))
    # digest is not available in the v1 API
    return timestamp, None


def _check_response_status(response: requests.Response) -> bool:
    """
    Check if the response status is OK. otherwise log an error and raise an exception

    Parameters
    ----------
    response: requests.Response
        The response object

    Returns
    -------
    bool
        True if the response status is OK, False otherwise
    """
    if response.status_code == 404:
        log.warning(f"Remote image info not found! {response.url}")
        return False
    elif response.status_code != 200:
        log.warning(
            "Remote image info could not be fetched! (%s) %s",
            response.status_code,
            response.url,
        )
        return False
    return True


def inspect_local_image_timestamp(
    docker_client: DockerClient,
    image: str,
    log: logging.Logger | ClickLogger = ClickLogger,
) -> tuple[datetime, str] | None:
    """
    Obtain creation timestamp object from local image.

    Parameters
    ----------
    docker_client: DockerClient
        Docker client
    image: str
        Image name
    log: logging.Logger | ClickLogger
        Logger

    Returns
    -------
    tuple[datetime, str] | None
        Timestamp containing the creation date and time of the local image and
        the image digest. If the image does not exist, None is returned.
    """
    try:
        img = docker_client.images.get(image)
    except docker.errors.ImageNotFound:
        log.debug(f"Local image does not exist! {image}")
        return None, None
    except docker.errors.APIError:
        log.debug(f"Local info not available! {image}")
        return None, None

    try:
        digest = img.attrs.get("RepoDigests")[0].split("@")[1]
    except Exception:
        digest = None
    timestamp = img.attrs.get("Created")
    timestamp = parse(timestamp)
    return timestamp, digest


def pull_if_newer(
    docker_client: DockerClient,
    image: str,
    log: logging.Logger | ClickLogger = ClickLogger,
) -> None:
    """
    Docker pull only if the remote image is newer.

    Parameters
    ----------
    docker_client: DockerClient
        A Docker client instance
    image: str
        Image to be pulled
    log: logger.Logger or ClickLogger
        Logger class

    Raises
    ------
    docker.errors.APIError
        If the image cannot be pulled
    """
    local_time, local_digest = inspect_local_image_timestamp(
        docker_client, image, log=log
    )
    remote_time, remote_digest = inspect_remote_image_timestamp(
        docker_client, image, log=log
    )
    pull = False
    if local_time and remote_time:
        if remote_digest == local_digest:
            log.debug(f"Local image is up-to-date: {image}")
        elif remote_time > local_time:
            log.debug(f"Remote image is newer: {image}")
            pull = True
        elif remote_time == local_time:
            log.debug(f"Local image is up-to-date: {image}")
        elif remote_time < local_time:
            log.warning(f"Local image is newer! Are you testing? {image}")
    elif local_time:
        log.warning(f"Only a local image has been found! {image}")
    elif remote_time:
        log.debug("No local image found, pulling from remote!")
        pull = True
    elif not local_time and not remote_time:
        log.warning(
            f"Cannot locate image {image} locally or remotely. Will try "
            "to pull it from Docker Hub..."
        )
        # we will try to pull it from the docker hub
        pull = True

    if pull:
        try:
            docker_client.images.pull(image)
            log.debug(f"Succeeded to pull image: {image}")
        except docker.errors.APIError as e:
            log.error(f"Failed to pull image! {image}")
            log.debug(e)
            raise docker.errors.APIError("Failed to pull image") from e


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
        log.warning("Removing container that was already running: " f"{container.name}")
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
        log.exception(f"Failed to remove container {container.name}")
        log.debug(e)


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


def delete_network(network: Network, kill_containers: bool = True) -> None:
    """Delete network and optionally its containers

    Parameters
    ----------
    network: Network
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
        log.info(f"Removing container {container.name} in old network")
        if kill_containers:
            log.warning(f"Killing container {container.name}")
            remove_container(container, kill=True)
        else:
            network.disconnect(container)
    # remove the network
    try:
        network.remove()
    except Exception:
        log.warning(f"Could not delete existing network {network.name}")


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
        log.warning("Could not delete volume %s", volume.name)
