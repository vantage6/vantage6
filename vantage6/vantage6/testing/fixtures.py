import pytest
import docker
import logging
import time
import random
import string

from pathlib import Path

from vantage6.common import logger_name
from vantage6.dev.profiles import ProfileManager


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def pytest_addoption(parser):
    """
    Add CLI options --dockerfile and --imagename,
    or read from pytest.ini with `dockerfile=...` or `imagename=...`
    """
    parser.addini("dockerfile", "Path to Dockerfile")
    parser.addini("imagename", "Docker image name")

    parser.addoption(
        "--dockerfile",
        action="store",
        default=None,
        help="Specify path to Dockerfile"
    )
    parser.addoption(
        "--imagename",
        action="store",
        default=None,
        help="Specify Docker image name"
    )

def build_test_image(dockerfile: Path, image_base_name: str):
    # Generate a (hopefully) unique Docker image name
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    random_suffix = "".join(random.choices(string.ascii_letters + string.digits, k=5))
    image_name = f"{image_base_name}:test-{timestamp}-{random_suffix}"

    docker_client = docker.from_env()

    log.info(f"Building Docker image '{image_name}'...")
    try:
        _, logs = docker_client.images.build(
            path=str(dockerfile), tag=image_name, rm=True
        )
        for log_line in logs:
            if "stream" in log_line:
                log.info(log_line["stream"].strip())
        log.info(f"Image '{image_name}' built successfully!")
    except docker.errors.BuildError as e:
        pytest.fail(f"Docker build failed: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error during Docker build: {e}")

    return image_name


def cleanup_test_image(image_name: str):
    log.info(f"Removing Docker image '{image_name}'...")
    try:
        docker_client = docker.from_env()
        image = docker_client.images.get(image_name)
        image_id = image.id

        # Remove the image to avoid polluting the host
        docker_client.images.remove(image=image_name, force=True)
        log.info(f"Image '{image_name}' removed successfully.")

        # TODO: is this sensible?
        # Remove dangling layers related to this image
        log.info("Checking for dangling layers related to the removed image...")
        dangling_images = docker_client.images.list(filters={"dangling": True})
        for dangling_image in dangling_images:
            if dangling_image.id == image_id:
                docker_client.images.remove(image=dangling_image.id, force=True)
                log.info(
                    f"Removed dangling layer '{dangling_image.id}' related to '{image_name}'."
                )
    except docker.errors.ImageNotFound:
        log.warning(f"Image '{image_name}' was already removed.")
    except Exception as e:
        log.error(f"Failed to remove image '{image_name}': {e}")


def run_profile():
    """
    Start a profile once for all tests in the session.
    """
    def _run_profile(profiles_json: Path, profile: str):
        profile_manager = ProfileManager(profiles_json)
        profile = profile_manager.get_profile(profile)
        log.info(f"Starting profile '{profile}'...")
        profile.start()

        yield profile

        log.info(f"Stopping profile '{profile}'...")
        profile.stop()

    return _run_profile


def wait_for_nodes():
    """
    Ensure the specified nodes are online.

    Parameters
    ----------
    client : Client
        The Vantage6 client instance.

    Returns
    -------
    callable
        A function to wait for nodes to come online.
    """
    def _wait_for_nodes(client, node_names, timeout=20, poll_interval=1):
        """
        Wait for the specified nodes to come online within a timeout.

        Parameters
        ----------
        client : Client
            The Vantage6 client instance.
        node_names : list
            List of node names to wait for
        timeout : int
            Maximum time to wait for nodes to be online, in seconds.
        poll_interval : int
            Time between checks, in seconds.

        Returns
        -------
        bool
            True if all specified nodes are online within the timeout.
        """
        target_nodes = set(node_names)
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = client.node.list(is_online=True)
            # FIXME: Ignoring pagination here
            nodes = response.get("data", [])
            online_node_names = {node.get("name") for node in nodes}

            missing_nodes = target_nodes - online_node_names
            if not missing_nodes:
                return True

            # Wait and retry
            time.sleep(poll_interval)

        # Timeout reached
        return False

    return _wait_for_nodes


# @pytest.fixture(scope="session")
# def docker_client():
#     """Fixture to create a Docker client."""
#     log.info("Creating Docker client...")
#     return docker.from_env()
