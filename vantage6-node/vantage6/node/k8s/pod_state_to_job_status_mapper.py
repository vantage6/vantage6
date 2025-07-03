from logging import Logger
from vantage6.common.enum import RunStatus
from kubernetes.client import V1Pod, V1PodStatus, V1ContainerStatus, V1PodCondition


terminal_k8s_phase_to_v6_status_map: dict[str, RunStatus] = {
    "Running": RunStatus.ACTIVE,
    "Failed": RunStatus.FAILED,
    "Succeded": RunStatus.COMPLETED,
    "Unknown": RunStatus.UNKNOWN_ERROR,
}

# Note on why ErrImagePull is not included: the ImagePullBackOff 'reason' will be eventually
# reported after multiple ErrImagePull events.
container_related_reasons_for_still_pending = {
    "ImagePullBackOff": "The pod is unable to pull the specified Docker image (authentication issues, network problems, or the image not existing in the registry) after multiple attempts.",
    "InvalidImageName": "The specified image name is malformed or invalid.",
    "ErrImageNeverPull": "ImagePullPolicy is Never, but the image doesn't exist locally",
    "ErrImagePull": "Failed to pull the image.",
}

runtime_pod_related_reasons_for_still_pending = {
    "CrashLoopBackOff": "The container keeps crashing repeatedly.",
    "CreateContainerConfigError": "Failed to create container due to misconfiguration.",
    "RunContainerError": "An error occurred while running the container.",
    "ContainerCannotRun": "The container failed to run.",
}

pod_initialization_related_reasons_for_still_pending = {
    "ContainerCreating": "Container image is being pulled and/or container is being created.",
    "PodInitializing": "Init containers are still running or haven't finished.",
}


def compute_job_pod_run_status(
    task_namespace: str, log: Logger, pod: V1Pod, label: str
) -> RunStatus:
    """
    Determines the current run status of a Kubernetes job pod based on its phase and container initialization status.
    This method inspects the provided Kubernetes pod object to map its current phase and, if applicable,
    the container's waiting reason to a corresponding `RunStatus` value used by the application.
    Args:
        pod: The Kubernetes pod object whose status is to be evaluated. It is expected to have a `status`
            attribute with `phase` and (optionally) `container_statuses`.
        label: A label identifying the job pod, used for logging purposes.
    Returns:
        RunStatus: The computed run status for the pod, which can be one of:
            - RunStatus.INITIALIZING: The pod is still pending for creation (for reasons other than missing/invalid Docker image).
            - RunStatus.NO_DOCKER_IMAGE: The pod is pending due to image pull errors or invalid image name.
            - RunStatus.ACTIVE: The pod is already running.
            - RunStatus.FAILED: The pod has failed.
            - RunStatus.COMPLETED: The pod has succeeded.
            - RunStatus.UNKNOWN_ERROR: The pod is in an unknown or unexpected phase.
    """

    pod_phase = pod.status.phase

    if pod_phase == "Pending":

        log.debug(
            "Job POD (label %s) is already in %s namespace, but still in pending status...",
            label,
            task_namespace,
        )

        pending_status_reason = None

        if pod.status and pod.status.container_statuses:
            # The job pods have use single container, container_statuses will always have a single element
            container_status: V1ContainerStatus = pod.status.container_statuses[0]
            if container_status.state.waiting:
                pending_status_reason = container_status.state.waiting.reason
                log.debug(
                    "Job POD (label %s, namespace %s) Still in pending phase. Container status: %s",
                    label,
                    task_namespace,
                    pending_status_reason,
                )
            else:
                log.debug(
                    "Job POD (label %s, namespace %s) Still in pending phase (container status not yet available)",
                    label,
                    task_namespace,
                )

        # If the 'pending' status is caused by an image/image-registry related problem, the corresponding status is returned.
        # Otherwise (e.g, the image is still being pulled "ImagePulling" ot the container is being created "ContainerCreating"),
        # an "INITIALIZING" status is returned.
        if pending_status_reason in container_related_reasons_for_still_pending:
            log.debug(
                "Job POD (label %s, namespace %s) - Reporting NO_DOCKER_IMAGE status: %s",
                label,
                task_namespace,
                container_related_reasons_for_still_pending[pending_status_reason],
            )
            return RunStatus.NO_DOCKER_IMAGE
        elif pending_status_reason in runtime_pod_related_reasons_for_still_pending:
            log.debug(
                "Job POD (label %s, namespace %s) - Reporting CRASHED status: %s",
                label,
                task_namespace,
                runtime_pod_related_reasons_for_still_pending[pending_status_reason],
            )
            return RunStatus.CRASHED
        elif (
            pending_status_reason
            in pod_initialization_related_reasons_for_still_pending
        ):
            log.debug(
                "Job POD (label %s, namespace %s) - Reporting INITIALIZING status: %s",
                label,
                task_namespace,
                pod_initialization_related_reasons_for_still_pending[
                    pending_status_reason
                ],
            )
            return RunStatus.INITIALIZING
        elif pending_status_reason != None:
            log.warning(
                "Job POD (label %s, namespace %s) - WARNING: the POD has an unknown/unsupported status: %s. Reporting this as an UNKNOWN error.",
                label,
                task_namespace,
                pending_status_reason,
            )
            return RunStatus.UNKNOWN_ERROR
        else:
            log.warning(
                "Job POD (label %s, namespace %s) - POD container(s) state information not yet available.",
                label,
                task_namespace,
                pending_status_reason,
            )
            return RunStatus.INITIALIZING

    # The POD is no longer pending, and a terminal phase has been reached: return the corresponding v6 status
    elif pod_phase in terminal_k8s_phase_to_v6_status_map:
        log.debug(
            "Job POD (label %s, namespace %s) - Reporting terminal status: %s",
            label,
            task_namespace,
            terminal_k8s_phase_to_v6_status_map[pod_phase],
        )
        return terminal_k8s_phase_to_v6_status_map[pod_phase]

    # No other kind of phase is expected to be reported (according to current k8s's specifications)
    else:
        log.critical(
            "Job (label %s, namespace %s) Unexpected/unhandled POD creation phase: %s. Reporting this as an UNKNOWN_ERROR.",
            label,
            task_namespace,
            pod_phase,
        )
        return RunStatus.UNKNOWN_ERROR
