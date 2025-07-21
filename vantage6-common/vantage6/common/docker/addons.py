import logging
import pathlib
import re
import json
import hashlib
from http import HTTPStatus

import requests
from requests.auth import HTTPBasicAuth

from docker.utils import parse_repository_tag
from docker.auth import resolve_repository_name

from vantage6.common import logger_name

log = logging.getLogger(logger_name(__name__))


# TODO v5+ remove these dummy functions - just to prevent import issues from v4 CLI for
# the time being
def check_docker_running() -> bool:
    return True


def pull_image(image: str) -> None:
    pass


def get_container() -> str:
    return ""


def remove_container() -> None:
    pass


def remove_container_if_exists() -> None:
    pass


def get_server_config_name() -> str:
    return ""


def get_num_nonempty_networks() -> int:
    return 0


def get_network() -> str:
    return None


def delete_network() -> None:
    pass


def delete_volume_if_exists() -> None:
    pass


def stop_container() -> None:
    pass


def running_in_docker() -> bool:
    """
    Check if this code is executed within a Docker container.

    Returns
    -------
    bool
        True if the code is executed within a Docker container, False otherwise
    """
    return pathlib.Path("/.dockerenv").exists()


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


def _get_manifest(
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


def get_digest(
    full_image: str,
    registry_username: str | None = None,
    registry_password: str | None = None,
) -> str:
    """
    Get digest of an image by fetching the manifest

    Parameters
    ----------
    full_image: str
        Image name. E.g. "harbor2.vantage6.ai/algorithms/average:latest"
    registry_username: str | None
        Registry username to authenticate with at the registry. Required if the image is
        private
    registry_password: str | None
        Registry password to authenticate with at the registry. Required if the image is
        private

    Returns
    -------
    str
        Digest of the image
    """
    try:
        manifest_response = _get_manifest(
            full_image, registry_username, registry_password
        )
    except ValueError as exc:
        log.warning("Could not get manifest of image %s", full_image)
        log.warning("Error: %s", exc)
        return ""
    if "Docker-Content-Digest" in manifest_response.headers:
        return manifest_response.headers["Docker-Content-Digest"]
    else:
        return __calculate_digest(manifest_response.json())


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
