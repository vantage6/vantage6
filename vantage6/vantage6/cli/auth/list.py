import click

from vantage6.common.globals import InstanceType

from vantage6.cli.common.list import get_configuration_list


@click.command()
def cli_auth_configuration_list() -> None:
    """
    Print the available auth configurations.
    """
    get_configuration_list(InstanceType.AUTH)
