from enum import Enum


class StorePolicies(str, Enum):
    """
    Enum for the different types of policies of the algorithm store.
    """

    ALGORITHM_VIEW = "algorithm_view"
    ALLOWED_SERVERS = "allowed_servers"
    ALLOW_LOCALHOST = "allow_localhost"
    MIN_REVIEWERS = "min_reviewers"
    ASSIGN_REVIEW_OWN_ALGORITHM = "assign_review_own_algorithm"
    MIN_REVIEWING_ORGANIZATIONS = "min_reviewing_organizations"


class AlgorithmViewPolicies(str, Enum):
    """Enum for available algorithm view policies"""

    PUBLIC = "public"
    WHITELISTED = "whitelisted"
    ONLY_WITH_EXPLICIT_PERMISSION = "private"
