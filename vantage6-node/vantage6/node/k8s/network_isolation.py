import time
import uuid
from logging import Logger

from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException

from vantage6.common.enum import AlgorithmStepType

from vantage6.node.globals import (
    ISOLATION_PROBE_CANDIDATES,
    ISOLATION_PROBE_CURL_MAX_TIME_SECONDS,
    ISOLATION_PROBE_IMAGE,
    ISOLATION_PROBE_TIMEOUT_SECONDS,
)


def _build_probe_command() -> list[str]:
    """
    Build a shell command that tries every probe candidate in turn, stopping as
    soon as one succeeds.

    Probing all candidates - rather than trusting a single one - avoids
    mistaking a blocked proxy or a single unreachable domain for network
    isolation.
    """
    checks = " || ".join(
        f"curl -s -o /dev/null --max-time {ISOLATION_PROBE_CURL_MAX_TIME_SECONDS} {url}"
        for url in ISOLATION_PROBE_CANDIDATES
    )
    return ["sh", "-c", checks]


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

    state = pod.status.container_statuses[0].state
    if state and state.terminated is not None:
        return state.terminated.exit_code == 0

    return False


def validate_algorithm_isolation(
    core_api: k8s_client.CoreV1Api,
    task_namespace: str,
    log: Logger,
) -> tuple[bool, str]:
    """
    Verify that central_compute pods cannot reach the public internet.

    Returns
    -------
    tuple[bool, str]
        (is_isolated, message) where is_isolated is True when egress to all
        probe targets is blocked.
    """
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
                metadata=k8s_client.V1ObjectMeta(
                    name=pod_name,
                    labels={
                        "role": AlgorithmStepType.CENTRAL_COMPUTE.value,
                        "app": "v6-isolation-probe",
                    },
                ),
                spec=k8s_client.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        k8s_client.V1Container(
                            name="probe",
                            image=ISOLATION_PROBE_IMAGE,
                            command=_build_probe_command(),
                        )
                    ],
                ),
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
