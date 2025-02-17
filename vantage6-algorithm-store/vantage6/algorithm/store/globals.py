from pathlib import Path
from enum import Enum

from vantage6.common.globals import APPNAME

#
#   INSTALLATION SETTINGS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent.parent

SERVER_MODULE_NAME = APPNAME + "-algorithm-store"

# TODO: this should be done differently
# Which resources should be initialized. These names correspond to the
# file-names in the resource directory
RESOURCES = [
    "version",
    "algorithm",
    "vantage6_server",
    "role",
    "rule",
    "user",
    "policy",
    "review",
]

# Where the resources modules have to be loaded from
RESOURCES_PATH = "vantage6.algorithm.store.resource"


class ConditionalArgComparator(str, Enum):
    """Enum containing allowed comparators for conditional arguments"""

    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_THAN_EQUALS = ">="
    LESS_THAN_EQUALS = "<="
