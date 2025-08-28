import click

from vantage6.common.globals import InstanceType

from vantage6.cli.common.new import new
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS


@click.command()
@click.option(
    "-n", "--name", default=None, help="Name of the configuration you want to use."
)
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Use system folders instead of user folders. This is the default",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=DEFAULT_SERVER_SYSTEM_FOLDERS,
    help="Use user folders instead of system folders",
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option(
    "--namespace",
    default=None,
    help="Kubernetes namespace to use",
)
def cli_algo_store_new(
    name: str, system_folders: bool, namespace: str, context: str
) -> None:
    """
    Create a new server configuration.
    """

    new(name, system_folders, namespace, context, InstanceType.ALGORITHM_STORE)
