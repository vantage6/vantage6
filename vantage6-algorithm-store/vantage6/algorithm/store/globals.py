# from pathlib import Path

from vantage6.common.globals import APPNAME

# TODO cleanup this file
#
#   INSTALLATION SETTINGS
#
# PACKAGE_FOLDER = Path(__file__).parent.parent.parent

SERVER_MODULE_NAME = APPNAME + "-algorithm-store"

# URL extension for the API endpoints
API_PATH = "/api"

# TODO: this should be done differently
# Which resources should be initialized. These names correspond to the
# file-names in the resource directory
RESOURCES = ["version", "algorithm", "vantage6_server", "role", "rule", "user"]
