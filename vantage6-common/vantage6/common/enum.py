import builtins
from enum import Enum

# Note: builtins.list is used in annotations below the list() classmethod, because
# that method shadows the builtin name within the class body.


class EnumBase(Enum):
    """Base class for all enums"""

    @classmethod
    def list(cls) -> list[str]:
        """Return a list of all the enum values"""
        return [status.value for status in cls]

    @classmethod
    def names(cls) -> builtins.list[str]:
        """Return a list of all the enum names"""
        return [status.name.lower() for status in cls]

    @classmethod
    def items(cls) -> builtins.list[tuple[str, str]]:
        """Return a list of (name, value) tuples for all enum members"""
        return [(status.name.lower(), status.value) for status in cls]


class StrEnumBase(str, EnumBase):
    """
    Base class for all string enums

    Equivalent to ``enum.StrEnum`` (Python 3.11+), which is used in vantage6 5.x
    but is not available on Python 3.10. Members always render as their value in
    ``str()``, ``format()`` and f-strings, so that e.g. container names and log
    file names are the same on every Python version
    (https://github.com/vantage6/vantage6/issues/2512).
    """

    def __str__(self) -> str:
        """Return the value of the enum member"""
        return str.__str__(self)

    def __format__(self, format_spec: str) -> str:
        """Format the value of the enum member"""
        return str.__format__(self, format_spec)


class StorePolicies(StrEnumBase):
    """
    Enum for the different types of policies of the algorithm store.
    """

    ALGORITHM_VIEW = "algorithm_view"
    ALLOWED_SERVERS = "allowed_servers"
    ALLOW_LOCALHOST = "allow_localhost"
    MIN_REVIEWERS = "min_reviewers"
    ASSIGN_REVIEW_OWN_ALGORITHM = "assign_review_own_algorithm"
    MIN_REVIEWING_ORGANIZATIONS = "min_reviewing_organizations"
    ALLOWED_REVIEWERS = "allowed_reviewers"
    ALLOWED_REVIEW_ASSIGNERS = "allowed_review_assigners"


class AlgorithmViewPolicies(StrEnumBase):
    """Enum for available algorithm view policies"""

    PUBLIC = "public"
    WHITELISTED = "whitelisted"
    ONLY_WITH_EXPLICIT_PERMISSION = "private"
