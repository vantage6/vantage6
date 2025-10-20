from vantage6.common import error
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import (
    find_running_service_names,
    get_config_name_from_helm_release_name,
    select_context_and_namespace,
    select_running_service,
)
from vantage6.cli.context import get_context
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.context.server import ServerContext


def get_and_select_ctx(
    instance_type: InstanceType,
    name: str,
    system_folders: bool,
    context: str,
    namespace: str,
    is_sandbox: bool,
) -> ServerContext | NodeContext | AlgorithmStoreContext:
    """
    Get and select the context for the given instance type.

    Parameters
    ----------
    instance_type : InstanceType
        The type of instance to get the context for
    name : str
        The name of the instance
    system_folders : bool
        Whether to use system folders or not
    context : str
        The Kubernetes context to use
    namespace : str
        The Kubernetes namespace to use
    is_sandbox : bool
        Whether the configuration is a sandbox configuration

    Returns
    -------
    ServerContext | NodeContext | AlgorithmStoreContext
        The context for the given instance type
    """
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )
    running_services = find_running_service_names(
        instance_type=instance_type,
        only_system_folders=False,
        only_user_folders=False,
        context=context,
        namespace=namespace,
        sandbox=is_sandbox,
    )

    if not running_services:
        error(f"No running {instance_type.value}s found.")
        exit(1)

    if not name:
        helm_name = select_running_service(running_services, instance_type)

        service_name = get_config_name_from_helm_release_name(
            helm_name, is_store=(instance_type == InstanceType.ALGORITHM_STORE)
        )
        ctx = get_context(
            instance_type, service_name, system_folders, is_sandbox=is_sandbox
        )

    else:
        ctx = get_context(instance_type, name, system_folders, is_sandbox=is_sandbox)
        helm_name = ctx.helm_release_name
        service_name = ctx.name

    if helm_name not in running_services:
        error(f"The {instance_type.value} {service_name} is not running.")
        exit(1)
    return ctx
