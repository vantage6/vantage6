from enum import Enum


class TaskStatus(str, Enum):
    """Enum to represent the status of a task"""

    # Task has not yet been started (usually, node is offline)
    PENDING = "pending"
    # Task is being started
    INITIALIZING = "initializing"
    # Container started without exceptions
    ACTIVE = "active"
    # Container exited and had zero exit code
    COMPLETED = "completed"

    # Generic fail status
    FAILED = "failed"
    # Failed to start the container on the first attempt
    START_FAILED = "start failed"
    # Could not start because docker image didn't exist
    NO_DOCKER_IMAGE = "non-existing Docker image"
    # Container had a non zero exit code
    CRASHED = "crashed"
    # Container was killed by user
    KILLED = "killed by user"
    # Task was not allowed by node policies
    NOT_ALLOWED = "not allowed"
    # Task failed without exit code
    UNKNOWN_ERROR = "unknown error"


def has_task_failed(status: TaskStatus) -> bool:
    """
    Check if task has failed to run to completion

    Parameters
    ----------
    status: TaskStatus | str
        The status of the task

    Returns
    -------
    bool
        True if task has failed, False otherwise
    """
    return status not in [
        TaskStatus.INITIALIZING,
        TaskStatus.ACTIVE,
        TaskStatus.COMPLETED,
        TaskStatus.PENDING,
    ]


def has_task_finished(status: TaskStatus) -> bool:
    """
    Check if task has finished or crashed

    Parameters
    ----------
    status: TaskStatus | str
        The status of the task

    Returns
    -------
    bool
        True if task has finished or failed, False otherwise
    """
    return has_task_failed(status) or status == TaskStatus.COMPLETED
