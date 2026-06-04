from pathlib import Path

from vantage6.common.globals import APPNAME

#
#   INSTALLATION SETTINGS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent

DATA_FOLDER = PACKAGE_FOLDER / APPNAME / "hq" / "_data"

HQ_MODULE_NAME = APPNAME + "-hq"

#
#   RUNTIME SETTINGS
#

# Where the resources modules have to be loaded from
RESOURCES_PATH = "vantage6.hq.resource"

# Which resources should be initialized. These names correspond to the
# file-names in the resource directory
RESOURCES = [
    "node",
    "collaboration",
    "organization",
    "task",
    "run",
    "blobstream",
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
]
