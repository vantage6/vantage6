from enum import Enum

from vantage6.common.enum import AlgorithmViewPolicies


class Partitioning(str, Enum):
    """Enum for types of algorithm partitioning"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class FunctionType(str, Enum):
    """Enum for function roles within the algorithm"""

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
    LINE = "line"


class ReviewStatus(str, Enum):
    """Enum for review status"""

    UNDER_REVIEW = "under review"
    APPROVED = "approved"
    REJECTED = "rejected"
    # reviews are dropped if the algorithm is invalidated while reviews were still open
    DROPPED = "dropped"


class AlgorithmStatus(str, Enum):
    """Enum for algorithm status

    Note that this contains all values from ReviewStatus but it also contains additional
    statuses.
    """

    AWAITING_REVIEWER_ASSIGNMENT = "awaiting reviewer assignment"
    UNDER_REVIEW = "under review"
    APPROVED = "approved"
    REJECTED = "rejected"

    # replaced by newer version
    REPLACED = "replaced"
    # removed from store without being replaced by newer version of the same algorithm
    REMOVED = "removed"


class PublicPolicies(str, Enum):
    """Enum to contain all policies that are publicly available"""

    # whether algorithms are visible to all users
    ALGORITHM_VIEW = "algorithm_view"
    # which servers are allowed to register users and therefore have access to modify
    # the resources in the algorithm store
    ALLOWED_SERVERS = "allowed_servers"


class BooleanPolicies(str, Enum):
    """Enum to contain all policies that are boolean"""

    # whether localhost servers are allowed to be registered. This should only be
    # allowed for local development servers and should be disabled in production
    ALLOW_LOCALHOST = "allow_localhost"
    ASSIGN_REVIEW_OWN_ALGORITHM = "assign_review_own_algorithm"


class ListPolicies(str, Enum):
    """Enum to contain all policies that are lists"""

    # which servers are allowed to edit algorithms
    ALLOWED_SERVERS = "allowed_servers"
    ALLOWED_REVIEWERS = "allowed_reviewers"
    ALLOWED_REVIEW_ASSIGNERS = "allowed_review_assigners"


class DefaultStorePolicies(Enum):
    """
    Enum for the default values of the policies of the algorithm store.
    """

    ALGORITHM_VIEW = AlgorithmViewPolicies.WHITELISTED.value
    ALLOWED_SERVERS = "all"
    ALLOW_LOCALHOST = False
    MIN_REVIEWERS = 2
    ASSIGN_REVIEW_OWN_ALGORITHM = False
    MIN_REVIEWING_ORGANIZATIONS = 2
    ALLOWED_REVIEWERS = None
    ALLOWED_REVIEW_ASSIGNERS = None
