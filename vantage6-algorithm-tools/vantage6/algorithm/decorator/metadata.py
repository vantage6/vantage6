import os
from dataclasses import dataclass
from functools import wraps
from pathlib import Path

import jwt

from vantage6.common.globals import ContainerEnvNames

from vantage6.algorithm.tools.util import info


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
    token_file: Path | None


def _extract_token_payload(token: str) -> dict:
    """
    Extract the payload from the token.

    Parameters
    ----------
    token: str
        The token as a string.

    Returns
    -------
    dict
        The payload as a dictionary. It contains the keys: `vantage6_client_type`,
        `node_id`, `organization_id`, `collaboration_id`, `task_id`, `image`,
        and `databases`.
    """
    jwt_payload = jwt.decode(token, options={"verify_signature": False})
    return jwt_payload["sub"]


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
        token = os.environ[ContainerEnvNames.CONTAINER_TOKEN.value]

        info("Extracting payload from token")
        payload = _extract_token_payload(token)

        metadata = RunMetaData(
            task_id=payload["task_id"],
            node_id=payload["node_id"],
            collaboration_id=payload["collaboration_id"],
            organization_id=payload["organization_id"],
            temporary_directory=Path(
                os.environ[ContainerEnvNames.SESSION_FOLDER.value]
            ),
            output_file=Path(os.environ[ContainerEnvNames.OUTPUT_FILE.value]),
            input_file=Path(os.environ[ContainerEnvNames.INPUT_FILE.value]),
            token=token,
        )
        return func(metadata, *args, **kwargs)

    decorator.vantage6_metadata_decorated = True

    return decorator
