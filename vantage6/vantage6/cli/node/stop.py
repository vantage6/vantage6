import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.stop import execute_stop, helm_uninstall, stop_port_forward
from vantage6.cli.globals import (
    DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL,
    InfraComponentName,
)


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Search for configuration in system folders instead of user folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Search for configuration in the user folders instead of "
    "system folders. This is the default.",
)
@click.option("--all", "all_nodes", flag_value=True, help="Stop all running nodes")
def cli_node_stop(
    name: str,
    context: str,
    namespace: str,
    system_folders: bool,
    all_nodes: bool,
) -> None:
    """
    Stop one or all running nodes.
    """
    execute_stop(
        stop_function=_stop_node,
        instance_type=InstanceType.NODE,
        infra_component=InfraComponentName.NODE,
        stop_all=all_nodes,
        to_stop=name,
        namespace=namespace,
        context=context,
        system_folders=system_folders,
    )


def _stop_node(node_name: str, namespace: str, context: str) -> None:
    """
    Stop a node

    Parameters
    ----------
    node_name : str
        Name of the node to stop
    namespace : str
        Kubernetes namespace to use
    context : str
        Kubernetes context to use
    """
    helm_uninstall(release_name=node_name, context=context, namespace=namespace)

    stop_port_forward(service_name=f"{node_name}-vantage6-node-service")

    info(f"Node {node_name} stopped successfully.")
