from enum import Enum
import time

from vantage6.common.globals import INTERVAL_MULTIPLIER, MAX_INTERVAL
from vantage6.algorithm.tools.util import info


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


def wait_for_task_completion(request_func, task_id: int, interval: float = 1) -> None:
    """
    Utility function to wait for a task to complete.

    Parameters
    ----------
    request_func : Callable
        Function to make requests to the server.
    task_id : int
        ID of the task to wait for.
    interval : float
        Initial interval in seconds between status checks.
    """
    t = time.time()

    while True:
        response = request_func(f"task/{task_id}/status")
        status = response.get("status")

        if has_task_finished(status):
            info(f"Task {task_id} completed in {int(time.time() - t)} seconds.")
            break

        info(f"Waiting for task {task_id}... ({int(time.time() - t)}s)", end="\r")
        time.sleep(interval)
        interval = min(interval * INTERVAL_MULTIPLIER, MAX_INTERVAL)
