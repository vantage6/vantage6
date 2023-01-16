from typing import Dict, Union

# TODO remove these imports, directly import from common
from vantage6.common import (
    logger_name,
    Singleton,
    bytes_to_base64s,
    base64s_to_bytes
)


def get_parent_id(task_dict: Dict) -> Union[int, None]:
    """
    Get a task's parent id from a JSON task dictionary

    Parameters
    ----------
    task_dict: Dict
        Dictionary with task information

    Returns
    -------
    parent_id: int or None
        Parent_id of the task
    """
    return task_dict['parent']['id'] \
        if task_dict['parent'] and 'id' in task_dict['parent'] else None
