import enum


class Partitioning(str, enum.Enum):
    """Enum for types of algorithm partitioning"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class FunctionType(str, enum.Enum):
    """Enum for types of partitioning"""

    CENTRAL = "central"
    FEDERATED = "federated"


class ArgumentType(str, enum.Enum):
    """Enum for argument types"""

    COLUMN = "column"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    JSON = "json"
    ORGANIZATIONS = "organizations"
    ORGANIZATION = "organization"
