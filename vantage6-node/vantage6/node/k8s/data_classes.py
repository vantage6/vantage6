from typing import NamedTuple


class Result(NamedTuple):
    """
    Data class to store the result of the docker image.

    Attributes
    ----------
    run_id: int
        ID of the current algorithm run
    logs: str
        Logs attached to current algorithm run
    data: str
        Output data of the algorithm
    status_code: int
        Status code of the algorithm run
    """

    run_id: int
    task_id: int
    logs: str
    data: str
    status: str
    parent_id: int | None


# Taken from docker_manager.py
class ToBeKilled(NamedTuple):
    """Data class to store which tasks should be killed"""

    task_id: int
    run_id: int
    organization_id: int


# Taken from docker_manager.py
class KilledRun(NamedTuple):
    """Data class to store which algorithms have been killed"""

    run_id: int
    task_id: int
    parent_id: int
