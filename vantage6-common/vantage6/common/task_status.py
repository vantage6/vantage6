from enum import Enum
from typing import Union


class TaskStatus(Enum):
    # Task has not yet been started (usually, node is offline)
    PENDING = 'pending'
    # Task is being started
    INITIALIZING = 'initializing'
    # Container started without exceptions
    STARTED = 'started'
    # Container exited and had zero exit code
    COMPLETED = 'completed'

    # Generic fail status
    FAILED = 'failed'
    # Failed to start the container on the first attempt
    START_FAILED = 'start failed'
    # Could not start because docker image didn't exist
    NO_DOCKER_IMAGE = 'non-existing Docker image'
    # Container had a non zero exit code
    CRASHED = 'crashed'
    # Container was killed by user
    KILLED = 'killed by user'


def has_task_failed(status: Union[TaskStatus, str]) -> bool:
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
    if isinstance(status, TaskStatus):
        return status not in [
            TaskStatus.INITIALIZING, TaskStatus.STARTED, TaskStatus.COMPLETED,
            TaskStatus.PENDING
        ]
    else:
        return status not in [
            TaskStatus.INITIALIZING.value, TaskStatus.STARTED.value,
            TaskStatus.COMPLETED.value, TaskStatus.PENDING.value
        ]
