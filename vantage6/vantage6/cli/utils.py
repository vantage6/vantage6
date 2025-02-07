"""
Utility functions for the CLI
"""

from __future__ import annotations

import re
import docker
import os
import questionary as q

from pathlib import Path

from vantage6.common import error, warning, info


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
