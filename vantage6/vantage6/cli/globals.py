"""
This module contains global variables that are used throughout the CLI.
"""

from enum import Enum
from pathlib import Path
from vantage6.common.globals import APPNAME

#
#   SERVER SETTINGS
#
DEFAULT_SERVER_SYSTEM_FOLDERS = True

#
#   NODE SETTINGS
#
DEFAULT_NODE_SYSTEM_FOLDERS = False

#
#   INSTALLATION SETTINGS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent

# FIXME BvB 22-06-28 think this is also defined in the node globals, and this
# one appears not to be used
NODE_PROXY_SERVER_HOSTNAME = "proxyserver"

DATA_FOLDER = PACKAGE_FOLDER / APPNAME / "_data"

# with open(Path(PACKAGE_FOLDER) / APPNAME / "cli" / "VERSION") as f:
#     VERSION = f.read()

# Maximum time to start up RabbitMQ in seconds
RABBIT_TIMEOUT = 300

# Location of repository to create new algorithm templates from
ALGORITHM_TEMPLATE_REPO = "gh:vantage6/v6-algorithm-template.git"

# image to use for diagnostics in `v6 test` commands
DIAGNOSTICS_IMAGE = "harbor2.vantage6.ai/algorithms/diagnostic"

# Address of community algorithm store
COMMUNITY_STORE = "https://store.cotopaxi.vantage6.ai/api"


class ServerType(str, Enum):
    """Enum containing server types"""

    V6SERVER = "server"
    ALGORITHM_STORE = "algorithm-store"


class ServerGlobals(str, Enum):
    """Enum containing server environment variables"""

    DB_URI_ENV_VAR = "VANTAGE6_DB_URI"
    CONFIG_NAME_ENV_VAR = "VANTAGE6_CONFIG_NAME"


class AlgoStoreGlobals(str, Enum):
    """Enum containing algorithm store environment variables"""

    DB_URI_ENV_VAR = "VANTAGE6_ALGO_STORE_DB_URI"
    CONFIG_NAME_ENV_VAR = "VANTAGE6_ALGO_STORE_CONFIG_NAME"
