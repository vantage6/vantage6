import time
import uuid
from collections.abc import Callable
from logging import Logger

from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException

from vantage6.common.enum import AlgorithmStepType

from vantage6.node.globals import (
    ISOLATION_PROBE_CANDIDATES,
    ISOLATION_PROBE_IMAGE,
    ISOLATION_PROBE_TIMEOUT_SECONDS,
)
from vantage6.node.runtime.probe import probe_args


def _probe_containers(
    image: str, build_container: Callable[..., k8s_client.V1Container]
) -> list[k8s_client.V1Container]:
    """
    One container per probe candidate, each trying to reach it.

    Probing all candidates - rather than trusting a single one - avoids
    mistaking a blocked proxy or a single unreachable domain for network
    isolation. Each candidate gets its own container because the hardened curl
    image has no shell to chain the attempts.
    """
    return [
        build_container(
            name=f"probe-{idx}",
            image=image,
            command=["curl"],
            args=probe_args(url),
        )
        for idx, url in enumerate(ISOLATION_PROBE_CANDIDATES)
    ]


def _wait_for_probe_pod(
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    pod_name: str,
    timeout_seconds: int,
) -> k8s_client.V1Pod:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        pod = core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
        phase = pod.status.phase
        if phase in ("Succeeded", "Failed"):
            return pod
        time.sleep(1)

    raise TimeoutError(
        f"Isolation probe pod '{pod_name}' did not complete within {timeout_seconds}s"
    )


def _probe_pod_reached_target(pod: k8s_client.V1Pod) -> bool:
    """
    Return True if the probe pod could reach the external target (not isolated).
    """
    if not pod.status or not pod.status.container_statuses:
        return False

    return any(
        status.state
        and status.state.terminated is not None
        and status.state.terminated.exit_code == 0
        for status in pod.status.container_statuses
    )


def validate_algorithm_isolation(
    core_api: k8s_client.CoreV1Api,
    task_namespace: str,
    log: Logger,
    labels: dict[str, str] | None = None,
    build_pod_spec: Callable[[list], k8s_client.V1PodSpec] | None = None,
    build_container: Callable[..., k8s_client.V1Container] | None = None,
    image: str = ISOLATION_PROBE_IMAGE,
) -> tuple[bool, str]:
    """
    Verify that central_compute pods cannot reach the public internet.

    ``labels``, ``build_pod_spec`` and ``build_container`` make the probe pod look
    like a central_compute algorithm pod, so that the same network policies,
    resources and security settings apply to it.

    Returns
    -------
    tuple[bool, str]
        (is_isolated, message) where is_isolated is True when egress to all
        probe targets is blocked.
    """
    if labels is None:
        labels = {
            "role": AlgorithmStepType.CENTRAL_COMPUTE.value,
            "app": "v6-isolation-probe",
        }
    if build_container is None:
        build_container = k8s_client.V1Container
    if build_pod_spec is None:

        def build_pod_spec(containers: list) -> k8s_client.V1PodSpec:
            return k8s_client.V1PodSpec(restart_policy="Never", containers=containers)

    pod_name = "v6-isolation-probe-" + str(uuid.uuid4())[:8]
    log.info(
        "Running algorithm network isolation probe in namespace '%s' using %s",
        task_namespace,
        ", ".join(ISOLATION_PROBE_CANDIDATES),
    )

    try:
        core_api.create_namespaced_pod(
            namespace=task_namespace,
            body=k8s_client.V1Pod(
                metadata=k8s_client.V1ObjectMeta(name=pod_name, labels=labels),
                spec=build_pod_spec(_probe_containers(image, build_container)),
            ),
        )
    except ApiException as exc:
        return False, (
            f"Failed to create isolation probe pod in namespace '{task_namespace}': "
            f"{exc}"
        )

    try:
        pod = _wait_for_probe_pod(
            core_api,
            task_namespace,
            pod_name,
            ISOLATION_PROBE_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        return False, str(exc)
    except ApiException as exc:
        return False, f"Failed to read isolation probe pod status: {exc}"
    finally:
        try:
            core_api.delete_namespaced_pod(
                name=pod_name,
                namespace=task_namespace,
                body=k8s_client.V1DeleteOptions(grace_period_seconds=0),
            )
        except ApiException as exc:
            if exc.status != 404:
                log.warning(
                    "Failed to delete isolation probe pod '%s': %s", pod_name, exc
                )

    if _probe_pod_reached_target(pod):
        return False, (
            "Algorithm containers can reach the public internet (probe targets: "
            f"{', '.join(ISOLATION_PROBE_CANDIDATES)}). This usually means "
            "Kubernetes NetworkPolicies are not enforced (e.g. Docker Desktop) or "
            f"are missing in namespace '{task_namespace}'"
        )

    return True, "Algorithm network isolation verified."
