import logging

from vantage6.common import logger_name

log = logging.getLogger(logger_name(__name__))


def get_parent_id(task_dict: dict) -> int | None:
    """
    Get a task's parent id from a JSON task dictionary

    Parameters
    ----------
    task_dict: Dict
        Dictionary with task information

    Returns
    -------
    parent_id: int | None
        Parent_id of the task
    """
    return (
        task_dict["parent"]["id"]
        if task_dict["parent"] and "id" in task_dict["parent"]
        else None
    )
