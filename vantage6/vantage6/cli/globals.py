"""
This module contains global variables that are used throughout the CLI.
"""

from pathlib import Path

from vantage6.common.enum import StrEnumBase
from vantage6.common.globals import APPNAME

#
#  CLI SETTINGS
#

DEFAULT_CLI_CONFIG_FOLDER = Path.home() / ".vantage6"
DEFAULT_CLI_CONFIG_FILE = DEFAULT_CLI_CONFIG_FOLDER / "config.yaml"

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
# TODO Check and remove
# HCR: This constants is indeed not used, as well as the other defined in node/globals.py
# NODE_PROXY_SERVER_HOSTNAME = "proxyserver"

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

DEFAULT_PROMETHEUS_IMAGE = "prom/prometheus"
PROMETHEUS_CONFIG = "prometheus.yml"
PROMETHEUS_DIR = "prometheus"

# template folder
TEMPLATE_FOLDER = PACKAGE_FOLDER / APPNAME / "cli" / "template"
SERVER_TEMPLATE_FILE = "server_config.j2"
NODE_TEMPLATE_FILE = "node_config.j2"
ALGO_STORE_TEMPLATE_FILE = "algo_store_config.j2"


# datasets included in the nodes of the dev network
class DefaultDatasets(StrEnumBase):
    """Enum containing default datasets"""

    OLYMPIC_ATHLETES = "olympic_athletes_2016.csv"
    KAPLAN_MEIER_TEST = "km_dataset.csv"


class ServerType(StrEnumBase):
    """Enum containing server types"""

    V6SERVER = "server"
    ALGORITHM_STORE = "algorithm-store"


class ChartName(StrEnumBase):
    """Enum containing chart names"""

    SERVER = "server"
    ALGORITHM_STORE = "store"
    NODE = "node"
    AUTH = "auth"
