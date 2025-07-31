from __future__ import annotations

import enum
import os
import re
import subprocess
import time
from os import PathLike
from pathlib import Path
from threading import Thread

import docker
from colorama import Fore, Style
from docker.client import DockerClient
from docker.models.containers import Container
from sqlalchemy.engine.url import make_url

from vantage6.common import error, info, warning
from vantage6.common.context import AppContext
from vantage6.common.docker.addons import check_docker_running, pull_image
from vantage6.common.globals import (
    APPNAME,
    DEFAULT_ALGO_STORE_IMAGE,
    DEFAULT_CHART_REPO,
    DEFAULT_DOCKER_REGISTRY,
    DEFAULT_NODE_IMAGE,
    DEFAULT_SERVER_IMAGE,
    DEFAULT_UI_IMAGE,
    InstanceType,
)

from vantage6.cli.common.utils import print_log_worker
from vantage6.cli.context import AlgorithmStoreContext, ServerContext
from vantage6.cli.globals import AlgoStoreGlobals, ServerGlobals
from vantage6.cli.utils import (
    check_config_name_allowed,
    validate_input_cmd_args,
)


def check_for_start(ctx: AppContext, type_: InstanceType) -> DockerClient:
    """
    Check if all requirements are met to start the instance.

    Parameters
    ----------
    ctx : AppContext
        The context object
    type_ : InstanceType
        The type of instance to check for

    Returns
    -------
    DockerClient
        A Docker client instance
    """
    # will print an error if not
    check_docker_running()

    info("Finding Docker daemon.")
    docker_client = docker.from_env()

    # check if name is allowed for docker volume, else exit
    check_config_name_allowed(ctx.name)

    # check that this server is not already running
    running_servers = docker_client.containers.list(
        filters={"label": f"{APPNAME}-type={type_}"}
    )
    for server in running_servers:
        if server.name == f"{APPNAME}-{ctx.name}-{ctx.scope}-{type_}":
            error(f"Server {Fore.RED}{ctx.name}{Style.RESET_ALL} is already running")
            exit(1)
    return docker_client


def get_image(
    image: str, ctx: AppContext, custom_image_key: str, default_image: str
) -> str:
    """
    Get the image name for the given instance type.

    Parameters
    ----------
    image : str | None
        The image name to use if specified
    ctx : AppContext
        The context object
    custom_image_key : str
        The key to look for in the config file
    default_image : str
        The default image name

    Returns
    -------
    str
        The image name to use
    """
    # Determine image-name. First we check if the option --image has been used.
    # Then we check if the image has been specified in the config file, and
    # finally we use the default settings from the package.
    if image is None:
        custom_images: dict = ctx.config.get("images")
        if custom_images:
            image = custom_images.get(custom_image_key)
        if not image:
            image = f"{DEFAULT_DOCKER_REGISTRY}/{default_image}"
    return image


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
        if not is_default_infra_image(image, instance_type):
            if image_exists_locally(client, image):
                warning("Failed to pull infrastructure image! Will use local image...")
            else:
                error("Failed to pull infrastructure image!")
                error("Image also not found locally. Exiting...")
                exit(1)
        else:
            error("Failed to pull infrastructure image! Exiting...")
            exit(1)


def is_default_infra_image(image: str, instance_type: InstanceType) -> bool:
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


def image_exists_locally(client: DockerClient, image: str) -> bool:
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


def mount_config_file(ctx: AppContext, config_file: str) -> list[docker.types.Mount]:
    """
    Mount the config file in the container.

    Parameters
    ----------
    ctx : AppContext
        The context object
    config_file : str
        The path to the config file

    Returns
    -------
    list[docker.types.Mount]
        The mounts to use
    """
    info("Creating mounts")
    return [docker.types.Mount(config_file, str(ctx.config_file), type="bind")]


def mount_source(mount_src: str) -> docker.types.Mount:
    """
    Mount the vantage6 source code in the container.

    Parameters
    ----------
    mount_src : str
        The path to the source code

    Returns
    -------
    docker.types.Mount | None
        The mount to use
    """
    if mount_src:
        mount_src = os.path.abspath(mount_src)
        return docker.types.Mount("/vantage6", mount_src, type="bind")


def mount_database(
    ctx: ServerContext | AlgorithmStoreContext, type_: InstanceType
) -> tuple[docker.types.Mount, dict]:
    """
    Mount database in the container if it is file-based (e.g. a SQLite DB).

    Parameters
    ----------
    ctx : AppContext
        The context object
    type_ : InstanceType
        The type of instance to mount the database for

    Returns
    -------
    docker.types.Mount | None
        The mount to use
    dict | None
        The environment variables to use
    """
    # FIXME: code duplication with cli_server_import()
    # try to mount database
    uri = ctx.config["uri"]
    url = make_url(uri)
    environment_vars = {}
    mount = None

    # If host is None, we're dealing with a file-based DB, like SQLite
    if url.host is None:
        db_path = url.database

        if not os.path.isabs(db_path):
            # We're dealing with a relative path here -> make it absolute
            db_path = ctx.data_dir / url.database

        basename = os.path.basename(db_path)
        dirname = os.path.dirname(db_path)
        os.makedirs(dirname, exist_ok=True)

        # we're mounting the entire folder that contains the database
        mount = docker.types.Mount("/mnt/database/", dirname, type="bind")

        if type_ == InstanceType.SERVER:
            environment_vars = {
                ServerGlobals.DB_URI_ENV_VAR.value: f"sqlite:////mnt/database/{basename}",
                ServerGlobals.CONFIG_NAME_ENV_VAR.value: ctx.config_file_name,
            }
        elif type_ == InstanceType.ALGORITHM_STORE:
            environment_vars = {
                AlgoStoreGlobals.DB_URI_ENV_VAR.value: f"sqlite:////mnt/database/{basename}",
                AlgoStoreGlobals.CONFIG_NAME_ENV_VAR.value: ctx.config_file_name,
            }
    else:
        warning(
            f"Database could not be transferred, make sure {url.host} "
            "is reachable from the Docker container"
        )
        info("Consider using the docker-compose method to start a server")

    return mount, environment_vars


# TODO v5+ remove this function, it is replaced by the `attach_logs` function in
# `vantage6.cli.common.utils`
def attach_logs(container: Container, type_: InstanceType) -> None:
    """
    Attach container logs to the console if specified.

    Parameters
    ----------
    container : Container
        The container to attach the logs from
    type_ : InstanceType
        The type of instance to attach the logs for
    """
    logs = container.attach(stream=True, logs=True, stdout=True)
    Thread(target=print_log_worker, args=(logs,), daemon=True).start()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            info("Closing log file. Keyboard Interrupt.")
            info(
                "Note that your server is still running! Shut it down "
                f"with {Fore.RED}v6 {type_} stop{Style.RESET_ALL}"
            )
            exit(0)


def helm_install(
    release_name: str,
    chart_name: str,
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
            f"Successfully installed release '{release_name}' using chart '{chart_name}'."
        )
    except subprocess.CalledProcessError as e:
        error(f"Failed to install release '{release_name}': {e.stderr}")
    except FileNotFoundError:
        error(
            "Helm command not found. Please ensure Helm is installed and available in the PATH."
        )


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
