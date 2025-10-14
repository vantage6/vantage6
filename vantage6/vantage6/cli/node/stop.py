import click

from vantage6.common import info, warning
from vantage6.common.globals import InstanceType

from vantage6.cli.common.stop import execute_stop, helm_uninstall, stop_port_forward
from vantage6.cli.common.utils import get_config_name_from_helm_release_name
from vantage6.cli.context import get_context
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
@click.option(
    "--sandbox", "is_sandbox", flag_value=True, help="Stop a sandbox environment"
)
def cli_node_stop(
    name: str,
    context: str,
    namespace: str,
    system_folders: bool,
    all_nodes: bool,
    is_sandbox: bool,
) -> None:
    """
    Stop one or all running nodes.
    """
    print("name", name)
    execute_stop(
        stop_function=_stop_node,
        stop_function_args={"system_folders": system_folders, "is_sandbox": is_sandbox},
        instance_type=InstanceType.NODE,
        infra_component=InfraComponentName.NODE,
        stop_all=all_nodes,
        to_stop=name,
        namespace=namespace,
        context=context,
        system_folders=system_folders,
        is_sandbox=is_sandbox,
    )


def _stop_node(
    node_helm_name: str,
    namespace: str,
    context: str,
    system_folders: bool,
    is_sandbox: bool,
) -> None:
    """
    Stop a node

    Parameters
    ----------
    node_helm_name : str
        Name of the node to stop
    namespace : str
        Kubernetes namespace to use
    context : str
        Kubernetes context to use
    system_folders: bool
        Whether to use the system folders or not
    is_sandbox: bool
        Whether node is a sandbox node or not
    """
    helm_uninstall(release_name=node_helm_name, context=context, namespace=namespace)

    stop_port_forward(service_name=f"{node_helm_name}-node-service")

    _stop_node_tasks(node_helm_name, system_folders, is_sandbox)

    info(f"Node {node_helm_name} stopped successfully.")


def _stop_node_tasks(
    node_helm_name: str, system_folders: bool, is_sandbox: bool
) -> None:
    """
    Stop the tasks of a node
    """
    node_name = get_config_name_from_helm_release_name(node_helm_name)
    node_ctx = get_context(
        InstanceType.NODE, node_name, system_folders, is_sandbox=is_sandbox
    )
    from pprint import pprint

    pprint(node_ctx.config)
    task_namespace = node_ctx.config.get("node", {}).get("taskNamespace")
    pprint(task_namespace)
    if not task_namespace:
        warning("Could not find node's task namespace. Node tasks will not be stopped.")
        return
