import click

from vantage6.common.globals import InstanceType

from vantage6.cli.common.list import get_configuration_list


@click.command()
def cli_hub_configuration_list() -> None:
    """
    Print the available hub configurations.
    """
    get_configuration_list(InstanceType.HUB)
