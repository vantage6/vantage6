import click

from vantage6.common.globals import InstanceType

from vantage6.cli.common.list import get_configuration_list


@click.command()
def cli_node_list() -> None:
    """
    Lists all node configurations.

    Note that this command cannot find node configuration files in custom
    directories.
    """
    get_configuration_list(InstanceType.NODE)
