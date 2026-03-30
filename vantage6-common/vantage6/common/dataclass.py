from dataclasses import dataclass
from typing import Self

from vantage6.common.enum import DatabaseType


@dataclass
class TaskDB:
    """
    Dataclass for a task database.

    This class is used to represent a database from a node configuration file - i.e. it
    is (mainly) used by the node and CLI, and not for user-facing code.

    Attributes
    ----------
    label: str
        The label of the database
    type: DatabaseType
        The type of the database
    uri: str
        The uri of the database
    """

    label: str
    type: DatabaseType
    uri: str
    is_file: bool | None = None
    is_dir: bool | None = None
    env: dict | None = None
    local_uri: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        if "label" not in data:
            raise ValueError("Database label is required")
        if "type" not in data:
            raise ValueError(
                f"Database with label {data['label']} is missing a type. "
                "Please provide a valid type."
            )
        if data["type"] not in DatabaseType.list():
            raise ValueError(
                f"Database with label {data['label']} has an invalid type: "
                f"{data['type']}. Please provide a valid type."
            )
        if "uri" not in data:
            raise ValueError(
                f"Database with label {data['label']} has no uri. "
                "Please provide a valid uri."
            )
        return cls(
            label=data["label"],
            type=DatabaseType(data["type"]),
            uri=data["uri"],
        )
