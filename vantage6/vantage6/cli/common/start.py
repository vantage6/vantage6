from __future__ import annotations

import re
import subprocess
import time
from os import PathLike
from pathlib import Path

import docker
from docker.client import DockerClient

from vantage6.common import error, info, warning
from vantage6.common.docker.addons import pull_image
from vantage6.common.globals import (
    DEFAULT_ALGO_STORE_IMAGE,
    DEFAULT_CHART_REPO,
    DEFAULT_DOCKER_REGISTRY,
    DEFAULT_NODE_IMAGE,
    DEFAULT_SERVER_IMAGE,
    DEFAULT_UI_IMAGE,
    InstanceType,
)

from vantage6.cli.globals import ChartName
from vantage6.cli.utils import validate_input_cmd_args


def pull_infra_image(
    client: DockerClient, image: str, instance_type: InstanceType
) -> None:
    """
    Try to pull an infrastructure image. If the image is a default infrastructure image,
    exit if in cannot be pulled. If it is not a default image, exit if it cannot be
    pulled and it is also not available locally. If a local image is available, a
    warning is printed.

    Parameters
    ----------
    client : DockerClient
        The Docker client
    image : str
        The image name to pull
    instance_type : InstanceType
        The type of instance to pull the image for
    """
    try:
        pull_image(client, image, suppress_error=True)
    except docker.errors.APIError:
        if not _is_default_infra_image(image, instance_type):
            if _image_exists_locally(client, image):
                warning("Failed to pull infrastructure image! Will use local image...")
            else:
                error("Failed to pull infrastructure image!")
                error("Image also not found locally. Exiting...")
                exit(1)
        else:
            error("Failed to pull infrastructure image! Exiting...")
            exit(1)


def _is_default_infra_image(image: str, instance_type: InstanceType) -> bool:
    """
    Check if an infrastructure image is the default image.

    Parameters
    ----------
    image : str
        The image name to check
    instance_type : InstanceType
        The type of instance to check the image for

    Returns
    -------
    bool
        True if the image is the default image, False otherwise
    """
    if instance_type == InstanceType.SERVER:
        return image == f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_SERVER_IMAGE}"
    elif instance_type == InstanceType.ALGORITHM_STORE:
        return image == f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_ALGO_STORE_IMAGE}"
    elif instance_type == InstanceType.UI:
        return image == f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_UI_IMAGE}"
    elif instance_type == InstanceType.NODE:
        return image == f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_NODE_IMAGE}"


def _image_exists_locally(client: DockerClient, image: str) -> bool:
    """
    Check if the image exists locally.

    Parameters
    ----------
    client : DockerClient
        The Docker client
    image : str
        The image name to check

    Returns
    -------
    bool
        True if the image exists locally, False otherwise
    """
    try:
        client.images.get(image)
    except docker.errors.ImageNotFound:
        return False
    return True


def helm_install(
    release_name: str,
    chart_name: ChartName,
    values_file: str | PathLike | None = None,
    context: str | None = None,
    namespace: str | None = None,
) -> None:
    """
    Manage the `helm install` command.

    Parameters
    ----------
    release_name : str
        The name of the Helm release.
    chart_name : str
        The name of the Helm chart.
    values_file : str, optional
        A single values file to use with the `-f` flag.
    context : str, optional
        The Kubernetes context to use.
    namespace : str, optional
        The Kubernetes namespace to use.
    """
    # Input validation
    validate_input_cmd_args(release_name, "release name")
    validate_input_cmd_args(chart_name, "chart name")

    values_file = Path(values_file) if values_file else None
    if values_file and not values_file.is_file():
        error(f"Helm chart values file does not exist: {values_file}")
        return

    validate_input_cmd_args(context, "context name", allow_none=True)
    validate_input_cmd_args(namespace, "namespace name", allow_none=True)

    # Create the command
    command = [
        "helm",
        "install",
        release_name,
        chart_name,
        "--repo",
        DEFAULT_CHART_REPO,
        # TODO v5+ remove this flag when we have a stable release
        "--devel",  # ensure using latest version including pre-releases
    ]

    if values_file:
        command.extend(["-f", str(values_file)])

    if context:
        command.extend(["--kube-context", context])

    if namespace:
        command.extend(["--namespace", namespace])

    try:
        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        info(
            f"Successfully installed release '{release_name}' using chart "
            f"'{chart_name}'."
        )
    except subprocess.CalledProcessError:
        error(f"Failed to install release '{release_name}'.")
        exit(1)
    except FileNotFoundError:
        error(
            "Helm command not found. Please ensure Helm is installed and available in "
            "the PATH."
        )
        exit(1)


def start_port_forward(
    service_name: str,
    service_port: int,
    port: int,
    ip: str | None,
    context: str | None = None,
    namespace: str | None = None,
) -> None:
    """
    Port forward a kubernetes service.

    Parameters
    ----------
    service_name : str
        The name of the Kubernetes service to port forward.
    service_port : int
        The port on the service to forward.
    port : int
        The port to listen on.
    ip : str | None
        The IP address to listen on. If None, defaults to localhost.
    context : str | None
        The Kubernetes context to use.
    namespace : str | None
        The Kubernetes namespace to use.
    """
    # Input validation
    validate_input_cmd_args(service_name, "service name")
    if not isinstance(service_port, int) or service_port <= 0:
        error(f"Invalid service port: {service_port}. Must be a positive integer.")
        return

    if not isinstance(port, int) or port <= 0:
        error(f"Invalid local port: {port}. Must be a positive integer.")
        return

    if ip and not re.match(
        r"^(localhost|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})$", ip
    ):
        error(f"Invalid IP address: {ip}. Must be a valid IPv4 address or 'localhost'.")
        return

    validate_input_cmd_args(context, "context name", allow_none=True)
    validate_input_cmd_args(namespace, "namespace name", allow_none=True)

    # Check if the service is ready before starting port forwarding
    info(f"Waiting for service '{service_name}' to become ready...")
    start_time = time.time()
    timeout = 300  # seconds
    while time.time() - start_time < timeout:
        try:
            result = (
                subprocess.check_output(
                    [
                        "kubectl",
                        "get",
                        "endpoints",
                        service_name,
                        "-o",
                        "jsonpath={.subsets[*].addresses[*].ip}",
                    ]
                )
                .decode()
                .strip()
            )

            if result:
                info(f"Service '{service_name}' is ready.")
                break
        except subprocess.CalledProcessError:
            pass  # ignore and retry

        time.sleep(2)
    else:
        error(
            f"Timeout: Service '{service_name}' has no ready endpoints after {timeout} seconds."
        )
        return

    # Create the port forwarding command
    if not ip:
        ip = "localhost"

    command = [
        "kubectl",
        "port-forward",
        "--address",
        ip,
        f"service/{service_name}",
        f"{port}:{service_port}",
    ]

    if context:
        command.extend(["--context", context])

    if namespace:
        command.extend(["--namespace", namespace])

    # Start the port forwarding process
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,  # Start in new session to detach from parent
        )

        # Give the process a moment to start and check if it's still running
        time.sleep(1)
        if process.poll() is not None:
            # Process has already terminated
            e = process.stderr.read().decode() if process.stderr else "Unknown error"
            error(f"Failed to start port forwarding: {e}")
            return

        info(
            f"Port forwarding started: {ip}:{port} -> {service_name}:{service_port} "
            f"(PID: {str(process.pid)})"
        )
        return
    except Exception as e:
        error(f"Failed to start port forwarding: {e}")
        return
