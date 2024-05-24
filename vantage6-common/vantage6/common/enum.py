from enum import Enum

POLICY_ALLOW_ALL = "all"


class StorePolicies(Enum):
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


class DefaultStorePolicies(Enum):
    """
    Enum for the default values of the policies of the algorithm store.
    """

    ALGORITHM_VIEW = AlgorithmViewPolicies.WHITELISTED.value
    ALLOWED_SERVERS = POLICY_ALLOW_ALL
    ALLOWED_SERVERS_EDIT = POLICY_ALLOW_ALL
    ALLOW_LOCALHOST = False
