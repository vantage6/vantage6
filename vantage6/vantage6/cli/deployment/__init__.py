"""
Where a vantage6 component runs. Kubernetes (with Helm) is the default; a node can
also run with Docker. The runtime is set by ``runtime`` in the configuration file.
"""

from vantage6.common.context import AppContext

KUBERNETES = "kubernetes"
DOCKER = "docker"
RUNTIMES = (KUBERNETES, DOCKER)


def runtime_of(ctx: AppContext) -> str:
    config = ctx.config if isinstance(ctx.config, dict) else {}
    runtime = config.get("runtime") or KUBERNETES
    if runtime not in RUNTIMES:
        raise ValueError(
            f"Unknown runtime '{runtime}' in {ctx.config_file}. Supported runtimes "
            f"are: {', '.join(RUNTIMES)}."
        )
    return runtime


def is_docker(ctx: AppContext) -> bool:
    return isinstance(ctx.config, dict) and ctx.config.get("runtime") == DOCKER


def node_config_runtimes(system_folders: bool) -> set[str]:
    """Runtimes used by the node configurations in the user or system folders."""
    from vantage6.cli.context.node import NodeContext

    runtimes = set()
    for is_sandbox in (False, True):
        configs, _ = NodeContext.available_configurations(system_folders, is_sandbox)
        for config in configs:
            runtimes.add((config.config or {}).get("runtime") or KUBERNETES)
    return runtimes


def docker_node_context(name: str | None, system_folders: bool, is_sandbox: bool):
    """Context of the named node if it is configured to run with Docker."""
    from vantage6.common.globals import InstanceType

    from vantage6.cli.context import get_context
    from vantage6.cli.context.node import NodeContext

    if not name or not NodeContext.config_exists(name, system_folders, is_sandbox):
        return None
    ctx = get_context(InstanceType.NODE, name, system_folders, is_sandbox=is_sandbox)
    return ctx if is_docker(ctx) else None


def get_node_deployment(ctx, **kubernetes_options):
    """
    The deployment of a node. ``kubernetes_options`` (context, namespace, chart
    settings, ...) only apply to nodes on Kubernetes.
    """
    if runtime_of(ctx) == DOCKER:
        from vantage6.cli.deployment.docker import DockerNodeDeployment

        return DockerNodeDeployment(ctx)

    from vantage6.cli.deployment.kubernetes import KubernetesNodeDeployment

    return KubernetesNodeDeployment(ctx, **kubernetes_options)
