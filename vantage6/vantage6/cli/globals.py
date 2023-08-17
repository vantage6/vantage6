"""
This module contains global variables that are used throughout the CLI.
"""
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

# Default port to start the UI on
DEFAULT_UI_PORT = 5001
