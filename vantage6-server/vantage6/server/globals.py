from pathlib import Path

from vantage6.common.globals import APPNAME

#
#   INSTALLATION SETTINGS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent

DATA_FOLDER = PACKAGE_FOLDER / APPNAME / "server" / "_data"

SERVER_MODULE_NAME = APPNAME + "-server"

#
#   RUNTIME SETTINGS
#

# Where the resources modules have to be loaded from
RESOURCES_PATH = "vantage6.server.resource"

# Which resources should be initialized. These names correspond to the
# file-names in the resource directory
RESOURCES = [
    "node",
    "collaboration",
    "organization",
    "task",
    "run",
    "token",
    "user",
    "version",
    "recover",
    "role",
    "rule",
    "health",
    "event",
    "algorithm_store",
    "study",
    "session",
    "dataframe",
    "ui.server_config",
]

# Super user information. This user is only created if it is not in the
# database yet at startup time.
SUPER_USER_INFO = {"username": "admin", "password": "admin"}
