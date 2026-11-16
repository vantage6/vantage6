import click

from vantage6.common import info

from vantage6.cli.common.attach import attach_logs
from vantage6.cli.common.utils import (
    extract_name_and_is_sandbox,
    select_running_service,
)
from vantage6.cli.context import InstanceType
from vantage6.cli.deployment import (
    KUBERNETES,
    docker_node_context,
    node_config_runtimes,
)
from vantage6.cli.deployment.docker import (
    DockerNodeDeployment,
    running_docker_node_contexts,
)
from vantage6.cli.globals import InfraComponentName
from vantage6.cli.k8s_config import select_k8s_config


@click.command()
@click.option("-n", "--name", default=None, help="Name of the configuration")
@click.option("--system", "system_folders", flag_value=True, help="Use system folders")
@click.option("--user", "system_folders", flag_value=False, help="Use user folders")
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--sandbox", "is_sandbox", flag_value=True, help="Attach to a sandbox environment"
)
def cli_node_attach(
    name: str | None,
    system_folders: bool,
    context: str,
    namespace: str,
    is_sandbox: bool,
) -> None:
    """
    Show the node logs in the current console.
    """
    info("Attaching to node logs...")
    if ctx := _docker_node_to_attach(name, system_folders, is_sandbox):
        DockerNodeDeployment(ctx).attach_logs()
        return

    k8s_config = select_k8s_config(context=context, namespace=namespace)
    attach_logs(
        name=name,
        instance_type=InstanceType.NODE,
        infra_component=InfraComponentName.NODE,
        system_folders=system_folders,
        k8s_config=k8s_config,
        is_sandbox=is_sandbox,
    )


def _docker_node_to_attach(name: str | None, system_folders: bool, is_sandbox: bool):
    """The Docker node to attach to, or None to use Kubernetes."""
    if name:
        name, is_sandbox = extract_name_and_is_sandbox(name, is_sandbox)
        return docker_node_context(name, system_folders, is_sandbox)
    running = running_docker_node_contexts(system_folders)
    if not running or KUBERNETES in node_config_runtimes(system_folders):
        return None
    choice = select_running_service(
        [ctx.deployment_name for ctx in running], InstanceType.NODE
    )
    return next(ctx for ctx in running if ctx.deployment_name == choice)
