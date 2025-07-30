from logging import Logger

from kubernetes.client import V1ContainerStatus, V1Pod

from vantage6.common.enum import RunStatus

# The phases that follow the 'Pending' one
#
#                      - Succeeded
#                     /
# Pending - Running ---- Failed
#                     \
#                      - Unknown
#
POST_PENDING_K8S_PHASE_TO_V6_STATUS_MAP: dict[str, RunStatus] = {
    "Running": RunStatus.ACTIVE,
    "Failed": RunStatus.FAILED,
    "Succeded": RunStatus.COMPLETED,
    "Unknown": RunStatus.UNKNOWN_ERROR,
}

# The reasons reported for a 'waiting' state on a POD's container (when the POD is
# Pending) related to container/image-related problems.
#
# Note: ErrImagePull is not included: the ImagePullBackOff 'reason' will be eventually
# reported after multiple ErrImagePull events.
CONTAINER_IMAGE_RELATED_REASONS_FOR_STILL_PENDING = {
    "ImagePullBackOff": (
        "The pod is unable to pull the specified Docker image authentication issues, "
        "network problems, or the image not existing in the registry) after multiple "
        "attempts."
    ),
    "InvalidImageName": "The specified image name is malformed or invalid.",
    "ErrImageNeverPull": (
        "ImagePullPolicy is Never, but the image doesn't exist locally"
    ),
    "ErrImagePull": "Failed to pull the image.",
}

# The reasons reported for a 'waiting' state on a POD's container (when the POD is
# Pending) related to a problem when creating or running a container
RUNTIME_POD_RELATED_REASONS_FOR_STILL_PENDING = {
    "CrashLoopBackOff": "The container keeps crashing repeatedly.",
    "CreateContainerConfigError": "Failed to create container due to misconfiguration.",
    "RunContainerError": "An error occurred while running the container.",
    "ContainerCannotRun": "The container failed to run.",
}

# The reasons reported for a 'waiting' state on a POD's container (when the POD is
# Pending) that are related to an ongoing image pull or container initialization
POD_INITIALIZATION_RELATED_REASONS_FOR_STILL_PENDING = {
    "ContainerCreating": (
        "Container image is being pulled and/or container is being created."
    ),
    "PodInitializing": "Init containers are still running or haven't finished.",
}


def compute_job_pod_run_status(
    task_namespace: str, log: Logger, pod: V1Pod, label: str
) -> RunStatus:
    """
    Maps the current phase and container status to one of the V6- RunStatuses

    This function inspects the provided Kubernetes pod object and maps its current state
    to a corresponding `RunStatus` value used by the application.

    Args:
        task_namespace (str): The Kubernetes namespace in which the pod is running.
        log (Logger): Logger instance for logging debug, warning, and critical messages.
        pod (V1Pod): The Kubernetes pod object whose status is to be evaluated.
        label (str): A label identifying the job or pod for logging purposes.

    Returns:
        RunStatus: The mapped run status corresponding to the pod's current state.
        Possible values include:
            - RunStatus.ACTIVE: If the pod is already with a Running status
            - RunStatus.FAILED: If the pod reported a Failed status
            - RunStatus.NO_DOCKER_IMAGE: If the pod is pending due to a missing or
              problematic Docker image.
            - RunStatus.CRASHED: If the pod is still in pending status but has reported
              a runtime crash.
            - RunStatus.INITIALIZING: If the pod is still initializing or waiting for
              image pull.
            - RunStatus.UNKNOWN_ERROR: If the pod is in an unexpected or unknown state.
            - RunStatus.COMPLETED: Not expected to happen but still possible: the job
              pod is reported as Succeded shortly after being created.


    """

    pod_phase = pod.status.phase

    if pod_phase == "Pending":
        log.debug(
            "Job POD (label %s) is already in %s namespace, but still in pending "
            "status...",
            label,
            task_namespace,
        )

        pending_status_reason = None

        # The POD has the container status available
        if pod.status and pod.status.container_statuses:
            # The job pods have use single container, container_statuses will always
            # have a single element
            container_status: V1ContainerStatus = pod.status.container_statuses[0]
            if container_status.state.waiting:
                pending_status_reason = container_status.state.waiting.reason
                log.debug(
                    "Job POD (label %s, namespace %s) Still in pending phase. "
                    "Container status: %s",
                    label,
                    task_namespace,
                    pending_status_reason,
                )

                # The reason the POD status is "Pending" is related to an docker-image
                # issue: NO_DOCKER_IMAGE
                if (
                    pending_status_reason
                    in CONTAINER_IMAGE_RELATED_REASONS_FOR_STILL_PENDING
                ):
                    log.debug(
                        "Job POD (label %s, namespace %s) - Reporting NO_DOCKER_IMAGE "
                        "status: %s",
                        label,
                        task_namespace,
                        CONTAINER_IMAGE_RELATED_REASONS_FOR_STILL_PENDING[
                            pending_status_reason
                        ],
                    )
                    return RunStatus.NO_DOCKER_IMAGE
                # The reason the POD status is "Pending" is due to an image that is
                # crashing: CRASHED
                elif (
                    pending_status_reason
                    in RUNTIME_POD_RELATED_REASONS_FOR_STILL_PENDING
                ):
                    log.debug(
                        "Job POD (label %s, namespace %s) - Reporting CRASHED status: "
                        "%s",
                        label,
                        task_namespace,
                        RUNTIME_POD_RELATED_REASONS_FOR_STILL_PENDING[
                            pending_status_reason
                        ],
                    )
                    return RunStatus.CRASHED
                # The reason the POD status is "Pending" is an image still being pulled
                # or intialized: INITIALIZING
                elif (
                    pending_status_reason
                    in POD_INITIALIZATION_RELATED_REASONS_FOR_STILL_PENDING
                ):
                    log.debug(
                        "Job POD (label %s, namespace %s) - Reporting INITIALIZING "
                        "status: %s",
                        label,
                        task_namespace,
                        POD_INITIALIZATION_RELATED_REASONS_FOR_STILL_PENDING[
                            pending_status_reason
                        ],
                    )
                    return RunStatus.INITIALIZING
                # The "Pending" status is caused by an unexpected reason
                else:
                    log.warning(
                        "Job POD (label %s, namespace %s) - WARNING: the POD has an "
                        "unknown/unsupported status: %s. Reporting this as an "
                        "UNKNOWN error.",
                        label,
                        task_namespace,
                        pending_status_reason,
                    )
                    return RunStatus.UNKNOWN_ERROR

            # The 'waiting' property and its details (the reason why the POD is in
            # 'Pending' state) are not available yet.
            else:
                log.debug(
                    "Job POD (label %s, namespace %s) Still in Pending phase, details "
                    "about the POD state are not available yet. ",
                    label,
                    task_namespace,
                )
                return RunStatus.INITIALIZING

        # The information about the POD status and its container(s) is not yet
        # available.
        else:
            log.warning(
                "Job POD (label %s, namespace %s) - POD container(s) state "
                "information not yet available.",
                label,
                task_namespace,
            )
            return RunStatus.INITIALIZING

    # The POD is no longer pending, and one of the phases that follows the 'Pending'
    # one has been reached: return the v6-status that correspond to such phase
    elif pod_phase in POST_PENDING_K8S_PHASE_TO_V6_STATUS_MAP:
        log.debug(
            "Job POD (label %s, namespace %s) - Reporting terminal status: %s",
            label,
            task_namespace,
            POST_PENDING_K8S_PHASE_TO_V6_STATUS_MAP[pod_phase],
        )
        return POST_PENDING_K8S_PHASE_TO_V6_STATUS_MAP[pod_phase]

    # No other kind of phase is expected to be reported (according to current k8s's
    # specifications)
    else:
        log.critical(
            "Job (label %s, namespace %s) Unexpected/unhandled POD creation phase: %s. "
            "Reporting this as an UNKNOWN_ERROR.",
            label,
            task_namespace,
            pod_phase,
        )
        return RunStatus.UNKNOWN_ERROR
