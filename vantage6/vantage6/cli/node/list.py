import click

from vantage6.common.globals import InstanceType

from vantage6.cli.common.list import get_configuration_list
from vantage6.cli.deployment import DOCKER, KUBERNETES, node_config_runtimes
from vantage6.cli.deployment.docker import running_docker_nodes


@click.command()
def cli_node_list() -> None:
    """
    Lists all node configurations.

    Note that this command cannot find node configuration files in custom
    directories.
    """
    runtimes = node_config_runtimes(False) | node_config_runtimes(True)
    get_configuration_list(
        InstanceType.NODE,
        query_helm=KUBERNETES in runtimes,
        other_running=running_docker_nodes() if DOCKER in runtimes else [],
        show_runtime=True,
    )
