# from pathlib import Path

from vantage6.common.globals import APPNAME

# TODO cleanup this file
#
#   INSTALLATION SETTINGS
#
# PACKAGE_FOLDER = Path(__file__).parent.parent.parent

SERVER_MODULE_NAME = APPNAME + "-algorithm-store"


# Which resources should be initialized. These names correspond to the
# file-names in the resource directory
RESOURCES = ['version', ]
