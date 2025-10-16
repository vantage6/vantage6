import click
from kubernetes import config as k8s_config
from kubernetes.config.config_exception import ConfigException
from kubernetes.stream import stream

from vantage6.common import error, info
from vantage6.common.globals import APPNAME, InstanceType

from vantage6.cli import __version__
from vantage6.cli.common.utils import select_context_and_namespace
from vantage6.cli.common.version import get_and_select_ctx
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
from vantage6.cli.utils_kubernetes import get_core_api_with_ssl_handling


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Search for configuration in system folders rather than user folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Search for configuration in user folders rather than "
    "system folders. This is the default",
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--sandbox", "is_sandbox", flag_value=True, help="Is this a sandbox environment?"
)
def cli_node_version(
    name: str, system_folders: bool, context: str, namespace: str, is_sandbox: bool
) -> None:
    """
    Returns current version of a vantage6 node.
    """
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )
    ctx = get_and_select_ctx(
        InstanceType.NODE, name, system_folders, context, namespace, is_sandbox
    )
    version = _get_node_version_from_k8s(ctx.helm_release_name, namespace, context)
    info("")
    info(f"Node version: {version}")
    info(f"CLI version: {__version__}")


def _get_node_version_from_k8s(
    helm_release: str,
    namespace: str,
    context: str,
) -> str:
    """
    Runs 'vnode-local version' in the node pod belonging to the Helm release.
    """
    pod = _get_pod_name_for_helm_release(helm_release, namespace, context)
    output = _exec_pod_command(
        pod_name=pod,
        namespace=namespace,
        command=["vnode-local", "version"],
    )
    return output.strip()


def _get_pod_name_for_helm_release(
    helm_release: str,
    namespace: str,
    context: str,
) -> str:
    """
    Returns the first pod name for a given Helm release in a namespace.
    Looks up pods using the standard Helm label 'app.kubernetes.io/instance'.
    """
    try:
        # Load kubeconfig (context optional). Falls back to in-cluster if not available.
        try:
            k8s_config.load_kube_config(context=context)  # desktop/dev
        except ConfigException:
            k8s_config.load_incluster_config()  # in-cluster
    except ConfigException as exc:
        raise RuntimeError(f"Failed to load Kubernetes config: {exc}") from exc

    core = get_core_api_with_ssl_handling()
    selector = f"app={APPNAME}-node,release={helm_release}"
    pods = core.list_namespaced_pod(namespace=namespace, label_selector=selector).items
    if not pods:
        error(f"No pods found for Helm release '{helm_release}' in ns '{namespace}'")
        exit(1)
    # Prefer a Ready pod
    for p in pods:
        for cond in p.status.conditions or []:
            if cond.type == "Ready" and cond.status == "True":
                return p.metadata.name
    # Fallback to first pod
    return pods[0].metadata.name


def _exec_pod_command(
    pod_name: str,
    namespace: str,
    command: list[str],
) -> str:
    """
    Executes a command inside the specified pod (and optional container) and returns stdout.
    """
    core = get_core_api_with_ssl_handling()
    resp = stream(
        core.connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
    )
    return resp
