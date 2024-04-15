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
    COLUMNS = "column_list"
    STRING = "string"
    STRINGS = "string_list"
    INTEGER = "integer"
    INTEGERS = "integer_list"
    FLOAT = "float"
    FLOATS = "float_list"
    BOOLEAN = "boolean"
    JSON = "json"
    ORGANIZATION = "organization"
    ORGANIZATIONS = "organization_list"


class VisualizationType(str, enum.Enum):
    """Enum for visualization types"""

    TABLE = "table"


class ReviewStatus(str, enum.Enum):
    """Enum for review status"""

    DRAFT = "draft"
    UNDER_REVIEW = "under review"
    APPROVED = "approved"
