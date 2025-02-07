import click
import questionary as q
import docker

from colorama import Fore, Style

from vantage6.common import error, info, debug
from vantage6.common.docker.addons import check_docker_running


@click.command()
def cli_node_clean() -> None:
    """
    Erase temporary Docker volumes.
    """
    check_docker_running()
    client = docker.from_env()

    # retrieve all volumes
    volumes = client.volumes.list()
    candidates = []
    msg = "This would remove the following volumes: "
    for volume in volumes:
        if volume.name[-6:] == "tmpvol":
            candidates.append(volume)
            msg += volume.name + ","
    info(msg)

    try:
        confirm = q.confirm("Are you sure?").unsafe_ask()
    except KeyboardInterrupt:
        confirm = False

    if confirm:
        for volume in candidates:
            try:
                volume.remove()
                # info(volume.name)
            except docker.errors.APIError as e:
                error(
                    f"Failed to remove volume {Fore.RED}'{volume.name}'"
                    f"{Style.RESET_ALL}. Is it still in use?"
                )
                debug(e)
                exit(1)
    info("Done!")
