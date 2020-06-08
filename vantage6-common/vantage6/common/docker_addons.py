import logging
import re

import docker
import requests
from dateutil.parser import parse

from vantage6.common import logger_name

logger = logger_name(__name__)
log = logging.getLogger(logger)
logging.basicConfig(level=logging.DEBUG)

client = docker.from_env()


def inspect_remote_image_timestamp(reg: str, rep: str, img: str,
                                   tag: str = "latest"):
    """
    Obtain creation timestamp object from remote image.

    Parameters
    ----------
    reg : str
        registry where the image is hosted
    rep : str
        repository in the registry
    img : str
        image name
    tag : str, optional
        image tag to be used, by default "latest"

    Returns
    -------
    datetime
        timestamp object containing the creation date and time of the image
    """
    image = f"https://{reg}/api/repositories/{rep}/{img}/tags/{tag}"

    result = requests.get(image)

    if result.status_code == 404:
        log.warning(f"Remote image not found! {image}")
        return None

    if result.status_code != 200:
        log.warning(f"Remote info could not be fetched! ({result.status_code})"
                    f"{image}")
        return None

    timestamp = result.json().get("created")
    timestamp = parse(timestamp)
    return timestamp


def inspect_local_image_timestamp(reg: str, rep: str, img: str,
                                  tag: str = "latest"):
    """
    Obtain creation timestamp object from local image.

    Parameters
    ----------
    reg : str
        registry where the image is hosted
    rep : str
        repository in the registry
    img : str
        image name
    tag : str, optional
        image tag to be used, by default "latest"

    Returns
    -------
    datetime
        timestamp object containing the creation date and time of the image
    """
    image = f"{reg}/{rep}/{img}:{tag}"
    try:
        img = client.images.get(image)
    except docker.errors.ImageNotFound:
        log.debug(f"Local image does not exist! {image}")
        return None
    except docker.errors.APIError:
        log.debug(f"Local info not available! {image}")
        return None

    timestamp = img.attrs.get("Created")
    timestamp = parse(timestamp)
    return timestamp


def pull_if_newer(image: str):
    """
    Docker pull only if the remote image is newer.

    Parameters
    ----------
    image : str
        image to be pulled
    """
    image_parts = re.split(r"[/:]", image)

    local_ = inspect_local_image_timestamp(*image_parts)
    remote_ = inspect_remote_image_timestamp(*image_parts)
    pull = False
    if local_ and remote_:
        if remote_ > local_:
            log.debug(f"Remote image is newer: {image}")
            pull = True
        elif remote_ == local_:
            log.debug(f"Local image is up-to-date: {image}")
        elif remote_ < local_:
            log.warning(f"Local image is newer! Are you testing? {image}")
    elif local_:
        log.warning(f"Only a local image has been found! {image}")
    elif remote_:
        log.debug("No local image present, pulling")
        pull = True
    elif not local_ and not remote_:
        log.error(f"Cannot locate image {image}")

    if pull:
        try:
            client.images.pull(image)
        except docker.errors.APIError as e:
            log.error(f"Failed to pull image! {image}")
            log.debug(e)
