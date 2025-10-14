import click
from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client import ApiException
from kubernetes.config.config_exception import ConfigException

from vantage6.common import error, info, warning
from vantage6.common.globals import APPNAME, InstanceType

from vantage6.cli.common.stop import execute_stop, helm_uninstall, stop_port_forward
from vantage6.cli.common.utils import get_config_name_from_helm_release_name
from vantage6.cli.context import get_context
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import (
    DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL,
    InfraComponentName,
)
from vantage6.cli.node.task_cleanup import delete_job_related_pods


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

    task_namespace = node_ctx.config.get("node", {}).get("taskNamespace")
    if not task_namespace:
        warning("Could not find node's task namespace. Node tasks will not be stopped.")
        return

    # detect tasks from the task namespace that this node is assigned to
    cleanup_task_jobs(task_namespace, node_ctx, all_nodes=False)


def cleanup_task_jobs(
    namespace: str, node_ctx: NodeContext | None = None, all_nodes: bool = False
) -> bool:
    """
    Cleanup Vantage6 task jobs in a given namespace.

    Parameters
    ----------
    namespace: str
        Namespace to cleanup
    node_ctx: NodeContext | None
        Node context to cleanup. If not given, all_nodes must be True.
    all_nodes: bool
        Cleanup all nodes. If not given, node_name must be given.

    Returns
    -------
    bool
        True if cleanup was successful, False otherwise
    """
    info(f"Cleaning up Vantage6 task jobs in namespace '{namespace}'")

    if not all_nodes and not node_ctx:
        error("Either all_nodes or node_ctx must be given to cleanup task jobs")
        return False

    # Load Kubernetes configuration (in-cluster first, fallback to kubeconfig)
    try:
        k8s_config.load_incluster_config()
    except ConfigException:
        try:
            k8s_config.load_kube_config()
        except ConfigException as exc:
            error(f"Failed to load Kubernetes configuration: {exc}")
            return False

    core_api = k8s_client.CoreV1Api()
    batch_api = k8s_client.BatchV1Api()

    jobs = _get_jobs(namespace, batch_api)

    deletions = 0
    for job in jobs:
        if not all_nodes and job.metadata.labels.get("node_id") != node_ctx.identifier:
            # if all_nodes is False, we should only delete jobs assigned to the current
            # node
            continue
        elif all_nodes and not _is_vantage6_task_job(job):
            # if all_nodes is True, we should only delete vantage6 task jobs, not other
            # jobs
            continue

        run_id = _get_job_run_id(job)
        if run_id is None:
            error(f"Job '{job.metadata.name}' has no run_id annotation, skipping...")
            continue

        # Use shared cleanup to delete job, pods and related secret
        job_name = job.metadata.name
        info(f"Deleting job '{job_name}' (run_id={run_id})")
        delete_job_related_pods(
            run_id=run_id,
            container_name=f"{APPNAME}-run-{run_id}",
            namespace=namespace,
            core_api=core_api,
            batch_api=batch_api,
        )
        deletions += 1

    if deletions == 0:
        info(f"No Vantage6 task jobs found to delete in namespace '{namespace}'")
    else:
        info(f"Deleted {deletions} Vantage6 task job(s) in namespace '{namespace}'")
    return True


def _is_vantage6_task_job(job: k8s_client.V1Job) -> bool:
    # Vantage6 task jobs can be identified by their name, which is of the form
    # "vantage6-run-<run_id>"
    return job.metadata.name.startswith(f"{APPNAME}-run-")


def _get_jobs(
    namespace: str, batch_api: k8s_client.BatchV1Api
) -> list[k8s_client.V1Job]:
    try:
        return batch_api.list_namespaced_job(namespace=namespace).items
    except ApiException as exc:
        error(f"Failed to list jobs in namespace {namespace}: {exc}")
        return []


def _get_job_run_id(job: k8s_client.V1Job) -> int | None:
    annotations = job.metadata.annotations or {}
    try:
        return int(annotations.get("run_id"))
    except ValueError:
        error(f"Job '{job.metadata.name}' has no run_id annotation, skipping")
        return None
