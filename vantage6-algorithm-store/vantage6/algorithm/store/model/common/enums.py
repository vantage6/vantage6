from enum import Enum


class Partitioning(str, Enum):
    """Enum for types of algorithm partitioning"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class FunctionType(str, Enum):
    """Enum for types of partitioning"""

    CENTRAL = "central"
    FEDERATED = "federated"


class ArgumentType(str, Enum):
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


class VisualizationType(str, Enum):
    """Enum for visualization types"""

    TABLE = "table"


class ReviewStatus(str, Enum):
    """Enum for review status"""

    DRAFT = "draft"
    UNDER_REVIEW = "under review"
    APPROVED = "approved"


class PublicPolicies(str, Enum):
    """Enum to contain all policies that are publically available"""

    # whether algorithms are visible to all users
    ALGORITHM_VIEW = "algorithm_view"
