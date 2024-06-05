from enum import Enum

POLICY_ALLOW_ALL = "all"


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


class StorePolicies(str, Enum):
    """
    Enum for the different types of policies of the algorithm store.
    """

    ALGORITHM_VIEW = "algorithm_view"
    ALLOWED_SERVERS = "allowed_servers"
    ALLOWED_SERVERS_EDIT = "allowed_servers_edit"
    ALLOW_LOCALHOST = "allow_localhost"


class AlgorithmViewPolicies(str, Enum):
    """Enum for available algorithm view policies"""

    PUBLIC = "public"
    WHITELISTED = "whitelisted"
    ONLY_WITH_EXPLICIT_PERMISSION = "private"


class PublicPolicies(str, Enum):
    """Enum to contain all policies that are publicly available"""

    # whether algorithms are visible to all users
    ALGORITHM_VIEW = "algorithm_view"


class BooleanPolicies(str, Enum):
    """Enum to contain all policies that are boolean"""

    # whether algorithms are visible to all users
    ALLOW_LOCALHOST = "allow_localhost"


class DefaultStorePolicies(Enum):
    """
    Enum for the default values of the policies of the algorithm store.
    """

    ALGORITHM_VIEW = AlgorithmViewPolicies.WHITELISTED.value
    ALLOWED_SERVERS = POLICY_ALLOW_ALL
    ALLOWED_SERVERS_EDIT = POLICY_ALLOW_ALL
    ALLOW_LOCALHOST = False
