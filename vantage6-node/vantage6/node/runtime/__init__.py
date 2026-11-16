from collections.abc import Callable

from vantage6.cli.context.node import NodeContext

from vantage6.node.runtime.base import ContainerRuntime

DEFAULT_RUNTIME = "kubernetes"


def _kubernetes() -> type[ContainerRuntime]:
    from vantage6.node.runtime.kubernetes.runtime import KubernetesRuntime

    return KubernetesRuntime


# Imported lazily, so that a node only needs the client library of its own runtime
RUNTIMES: dict[str, Callable[[], type[ContainerRuntime]]] = {
    "kubernetes": _kubernetes,
}


def runtime_name(ctx: NodeContext) -> str:
    return ctx.config.get("container_runtime") or DEFAULT_RUNTIME


def get_runtime(ctx: NodeContext) -> ContainerRuntime:
    name = runtime_name(ctx)
    if name not in RUNTIMES:
        raise ValueError(
            f"Unknown container runtime '{name}'. Supported runtimes are: "
            f"{', '.join(RUNTIMES)}."
        )
    return RUNTIMES[name]()(ctx)
