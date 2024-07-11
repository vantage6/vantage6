import click

from vantage6.common.docker.addons import check_docker_running
from vantage6.common.globals import InstanceType
from vantage6.cli.common.utils import get_server_configuration_list


@click.command()
def cli_server_configuration_list() -> None:
    """
    Print the available server configurations.
    """
    check_docker_running()
    get_server_configuration_list(InstanceType.SERVER)
