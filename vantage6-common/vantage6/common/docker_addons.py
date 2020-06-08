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


def inspect_remote_image_timestamp(reg, rep, img, tag="latest"):
    """Retrieve timestamp of the remote image.

        >>> inspect_remote_image_timestamp("harbor.vantage6.ai",
        ...                                 "infrastructure", "node")
        datetime.datetime(2020, 5, 18, 14, 33, 45, 420900, tzinfo=tzutc())
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


def inspect_local_image_timestamp(reg, rep, img, tag="latest"):
    """Retrieve timestamp of the local image.

        >>> inspect_local_image_timestamp("harbor.vantage6.ai",
        ...                                 "infrastructure", "node")
        datetime.datetime(2020, 5, 18, 14, 33, 45, 420900, tzinfo=tzutc())
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


def pull_if_newer(image):
    """Only pull the image if the remote is newer.

        >>> pull_if_newer("registry/repository/image:tag")
        >>> pull_if_newer("registry/repository/image")

        >>> pull_if_newer("harbor.vantage6.ai/vantage/vtg.chisq:trolltunga")
        >>> pull_if_newer("harbor.vantage6.ai/infrastructure/node:latest")
        >>> pull_if_newer("harbor.vantage6.ai/infrastructure/server:latest")
        >>> pull_if_newer("harbor.vantage6.ai/infrastructure/server1:latest")
        >>> pull_if_newer("harbor.vantage6.ai/infrastructure/node")
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
