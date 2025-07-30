from vantage6.common.enum import AlgorithmViewPolicies, EnumBase


class Partitioning(EnumBase):
    """Enum for types of algorithm partitioning"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class VisualizationType(EnumBase):
    """Enum for visualization types"""

    TABLE = "table"
    LINE = "line"


class ReviewStatus(EnumBase):
    """Enum for review status"""

    UNDER_REVIEW = "under review"
    APPROVED = "approved"
    REJECTED = "rejected"
    # reviews are dropped if the algorithm is invalidated while reviews were still open
    DROPPED = "dropped"


class AlgorithmStatus(EnumBase):
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


class PublicPolicies(EnumBase):
    """Enum to contain all policies that are publicly available"""

    # whether algorithms are visible to all users
    ALGORITHM_VIEW = "algorithm_view"


class BooleanPolicies(EnumBase):
    """Enum to contain all policies that are boolean"""

    ASSIGN_REVIEW_OWN_ALGORITHM = "assign_review_own_algorithm"


class ListPolicies(EnumBase):
    """Enum to contain all policies that are lists"""

    ALLOWED_REVIEWERS = "allowed_reviewers"
    ALLOWED_REVIEW_ASSIGNERS = "allowed_review_assigners"


class DefaultStorePolicies(EnumBase):
    """
    Enum for the default values of the policies of the algorithm store.
    """

    ALGORITHM_VIEW = AlgorithmViewPolicies.AUTHENTICATED.value
    MIN_REVIEWERS = 2
    ASSIGN_REVIEW_OWN_ALGORITHM = False
    MIN_REVIEWING_ORGANIZATIONS = 2
    ALLOWED_REVIEWERS = None
    ALLOWED_REVIEW_ASSIGNERS = None
