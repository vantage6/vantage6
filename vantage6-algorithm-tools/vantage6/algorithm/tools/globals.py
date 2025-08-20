from pathlib import Path
from enum import Enum

from vantage6.common.globals import APPNAME

#
#   INSTALLATION SETTINGS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent.parent

SERVER_MODULE_NAME = APPNAME + "-algorithm-tools"


class ConditionalArgComparator(str, Enum):
    """Enum containing allowed comparators for conditional arguments"""

    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_THAN_EQUALS = ">="
    LESS_THAN_EQUALS = "<="
