import re

from vantage6.common import error


def check_config_name_allowed(name: str) -> None:
    """ Check if configuration name is allowed """
    if not re.match('^[a-zA-Z0-9_.-]+$', name):
        error(f"Name '{name}' is not allowed. Please use only the following "
              "characters: a-zA-Z0-9_.-")
        exit(1)


def check_if_docker_deamon_is_running(docker_client):
    try:
        docker_client.ping()
    except Exception:
        error("Docker socket can not be found. Make sure Docker is running.")
        exit(1)
