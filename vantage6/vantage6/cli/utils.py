"""
Utility functions for the CLI
"""

from __future__ import annotations

import re
import docker
import os
import time
import socket
import questionary as q
import logging

from pathlib import Path

from vantage6.common import error, logger_name, warning, info

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

def check_config_name_allowed(name: str) -> None:
    """
    Check if configuration name is allowed

    Parameters
    ----------
    name : str
        Name to be checked
    """
    if name.count(" ") > 0:
        name = name.replace(" ", "-")
        info(f"Replaced spaces from configuration name: {name}")
    if not re.match("^[a-zA-Z0-9_.-]+$", name):
        error(
            f"Name '{name}' is not allowed. Please use only the following "
            "characters: a-zA-Z0-9_.-"
        )
        # FIXME: FM, 2023-01-03: I dont think this is a good side effect. This
        # should be handled by the caller.
        exit(1)


def check_if_docker_daemon_is_running(docker_client: docker.DockerClient) -> None:
    """
    Check if Docker daemon is running

    Parameters
    ----------
    docker_client : docker.DockerClient
        The docker client
    """
    try:
        docker_client.ping()
    except Exception:
        error("Docker socket can not be found. Make sure Docker is running.")
        exit(1)


def remove_file(file: str | Path, file_type: str) -> None:
    """
    Remove a file if it exists.

    Parameters
    ----------
    file : str
        absolute path to the file to be deleted
    file_type : str
        type of file, used for logging
    """
    if os.path.isfile(file):
        info(f"Removing {file_type} file: {file}")
        try:
            os.remove(file)
        except Exception as e:
            error(f"Could not delete file: {file}")
            error(e)
    else:
        warning(f"Could not remove {file_type} file: {file} does not exist")


def prompt_config_name(name: str | None) -> None:
    """
    Get a new configuration name from the user, or simply return the name if
    it is not None.

    Parameters
    ----------
    name : str
        Name to be checked

    Returns
    -------
    str
        The name of the configuration
    """
    if not name:
        try:
            name = q.text("Please enter a configuration-name:").unsafe_ask()
        except KeyboardInterrupt:
            error("Aborted by user!")
            exit(1)
        if name.count(" ") > 0:
            name = name.replace(" ", "-")
            info(f"Replaced spaces from configuration name: {name}")
    return name

def wait_debug_dap_ready(host: str, port: int, timeout: int = 20) -> bool:
    """
    Keeps attempting to connect to the specified host and port, waiting for the
    response to begin with 'Content-Length:'. This serves as a simple and
    (far-from-perfect) indication that the Debug Adapter Protocol (DAP) adapter
    is ready to accept client connections.
    See: https://microsoft.github.io/debug-adapter-protocol/

    Parameters
    ----------
    host : str
        Host where the DAP adapter is excepected to be running.
    port : int
        Port where the DAP adapter is excepected to be running.
    timeout : int
        Maximum time to wait (in seconds) before timing out.

    Returns
    -------
    bool
        True if DAP adapter sems to be ready, False otherwise.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # open new TCP connection
            with socket.create_connection((host, port), timeout=1) as sock:
                log.debug("Connected to %s:%s, checking response...", host, port)

                # read the first response from the connection
                response = sock.recv(128).decode()
                if response.startswith("Content-Length:"):
                    log.debug("Content-Length found!")
                    return True
                # TODO: check for other responses and error?
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            log.debug("Connection attempt failed: %s", e)

        # wait before retry
        time.sleep(1)

    log.debug("Timeout reached without receiving 'Content-Length' from %s:%s.", host, port)
    return False

