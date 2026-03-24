from dataclasses import dataclass
from typing import Self

from marshmallow import ValidationError

from vantage6.common.enum import TaskDatabaseType


@dataclass
class CreateTaskDB:
    type: TaskDatabaseType
    label: str | None = None
    dataframe_id: int | None = None

    @classmethod
    def from_dict(cls, database: dict) -> Self:
        if "type" not in database:
            raise ValidationError("Each database must have a 'type' key")
        if database["type"] == TaskDatabaseType.DATAFRAME and not database.get(
            "dataframe_id"
        ):
            raise ValidationError(
                "Database of type 'dataframe' must have a 'dataframe_id' key"
            )
        elif database["type"] != TaskDatabaseType.DATAFRAME and not database.get(
            "label"
        ):
            raise ValidationError(
                f"Database of type '{database['type']}' must have a 'label' key"
            )

        # check that there are no other keys in the database
        allowed_keys = {"label", "type", "dataframe_id"}
        if not set(database.keys()).issubset(cls.__annotations__.keys()):
            raise ValidationError(
                f"Database {database} contains unknown keys. Allowed keys "
                f"are {allowed_keys}."
            )

        return cls(
            type=TaskDatabaseType(database["type"]),
            label=database.get("label"),
            dataframe_id=database.get("dataframe_id"),
        )

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "type": self.type.value,
            "dataframe_id": self.dataframe_id,
        }
