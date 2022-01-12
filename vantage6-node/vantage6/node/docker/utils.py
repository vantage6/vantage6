import pathlib


def running_in_docker() -> bool:
    """Return True if this code is executed within a Docker container."""
    return pathlib.Path('/.dockerenv').exists()
