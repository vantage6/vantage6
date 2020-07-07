import logging
import re

import docker
import requests

from dateutil.parser import parse

from vantage6.common import logger_name
from vantage6.common import ClickLogger

logger = logger_name(__name__)
log = logging.getLogger(logger)

docker_client = docker.from_env()

# logger needs to be setable as logging is used both inside and outside
# our man application


def inspect_remote_image_timestamp(image: str, log=ClickLogger):
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
    # check if a tag has been profided

    image_tag = re.split(":", image)
    img = image_tag[0]
    tag = image_tag[1] if len(image_tag) == 2 else "latest"

    try:
        reg, rep, img_ = re.split("/", img)
    except ValueError:
        log.warn("Could not construct remote URL, "
                 "are you using a local image?")
        return

    image = f"https://{reg}/api/repositories/{rep}/{img_}/tags/{tag}"

    result = requests.get(image)

    if result.status_code == 404:
        log.warn(f"Remote image not found! {image}")
        return None

    if result.status_code != 200:
        log.warn(f"Remote info could not be fetched! ({result.status_code})"
                 f"{image}")
        return

    timestamp = result.json().get("created")
    timestamp = parse(timestamp)
    return timestamp


def inspect_local_image_timestamp(image: str, log=ClickLogger):
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
    # p = re.split(r"[/:]", image)
    # if len(p) == 4:
    #     image = f"{p[0]}/{p[1]}/{p[2]}:{p[3]}"

    try:
        img = docker_client.images.get(image)
    except docker.errors.ImageNotFound:
        log.debug(f"Local image does not exist! {image}")
        return None
    except docker.errors.APIError:
        log.debug(f"Local info not available! {image}")
        return None

    timestamp = img.attrs.get("Created")
    timestamp = parse(timestamp)
    return timestamp


def pull_if_newer(image: str, log=ClickLogger):
    """
    Docker pull only if the remote image is newer.

    Parameters
    ----------
    image : str
        image to be pulled
    """

    local_ = inspect_local_image_timestamp(image, log=log)
    remote_ = inspect_remote_image_timestamp(image, log=log)
    pull = False
    if local_ and remote_:
        if remote_ > local_:
            log.debug(f"Remote image is newer: {image}")
            pull = True
        elif remote_ == local_:
            log.debug(f"Local image is up-to-date: {image}")
        elif remote_ < local_:
            log.warn(f"Local image is newer! Are you testing? {image}")
    elif local_:
        log.warn(f"Only a local image has been found! {image}")
    elif remote_:
        log.debug("No local image found, pulling from remote!")
        pull = True
    elif not local_ and not remote_:
        log.error(f"Cannot locate image {image}")

    if pull:
        try:
            docker_client.images.pull(image)
        except docker.errors.APIError as e:
            log.error(f"Failed to pull image! {image}")
            log.debug(e)
