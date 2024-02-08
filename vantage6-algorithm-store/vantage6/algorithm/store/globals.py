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

# Which resources should be initialized. These names correspond to the
# file-names in the resource directory
RESOURCES = ["version", "algorithm", "vantage6_server"]

# environment variable name for host URI
HOST_URI_ENV = "HOST_URI_ENV_VAR"
