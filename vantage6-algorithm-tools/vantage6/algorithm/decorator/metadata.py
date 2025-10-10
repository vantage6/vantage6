import os
from dataclasses import dataclass
from functools import wraps
from pathlib import Path

from vantage6.common.enum import AlgorithmStepType
from vantage6.common.globals import ContainerEnvNames

from vantage6.algorithm.tools.util import get_action


@dataclass
class RunMetaData:
    """Dataclass containing metadata of the run."""

    task_id: int | None
    node_id: int | None
    collaboration_id: int | None
    organization_id: int | None
    temporary_directory: Path | None
    output_file: Path | None
    input_file: Path | None
    token: str | None
    action: AlgorithmStepType | None


def metadata(func: callable) -> callable:
    @wraps(func)
    def decorator(*args, **kwargs) -> callable:
        """
        Decorator the function with metadata from the run.

        Decorator that adds metadata from the run to the function. This
        includes the task id, node id, collaboration id, organization id,
        temporary directory, output file, input file, and token file.

        Example
        -------
        >>> @metadata
        >>> def my_algorithm(metadata: RunMetaData, <other arguments>):
        >>>     pass
        """
        action = get_action()

        token = None
        if action == AlgorithmStepType.CENTRAL_COMPUTE:
            token = os.environ[ContainerEnvNames.CONTAINER_TOKEN.value]

        metadata = RunMetaData(
            task_id=os.environ[ContainerEnvNames.TASK_ID.value],
            node_id=os.environ[ContainerEnvNames.NODE_ID.value],
            collaboration_id=os.environ[ContainerEnvNames.COLLABORATION_ID.value],
            organization_id=os.environ[ContainerEnvNames.ORGANIZATION_ID.value],
            temporary_directory=Path(
                os.environ[ContainerEnvNames.SESSION_FOLDER.value]
            ),
            output_file=Path(os.environ[ContainerEnvNames.OUTPUT_FILE.value]),
            input_file=Path(os.environ[ContainerEnvNames.INPUT_FILE.value]),
            token=token,
            action=action.value,
        )
        return func(metadata, *args, **kwargs)

    decorator.vantage6_metadata_decorated = True

    return decorator
