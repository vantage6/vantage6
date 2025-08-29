import click

from vantage6.common.globals import InstanceType

from vantage6.cli.common.new import new
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Store this configuration in the system folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Store this configuration in the user folders. This is the default.",
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option(
    "--namespace",
    default=None,
    help="Kubernetes namespace to use",
)
def cli_node_new_configuration(
    name: str,
    system_folders: bool,
    namespace: str,
    context: str,
) -> None:
    """
    Create a new node configuration.

    Checks if the configuration already exists. If this is not the case
    a questionnaire is invoked to create a new configuration file.
    """
    new(name, system_folders, namespace, context, InstanceType.NODE)
