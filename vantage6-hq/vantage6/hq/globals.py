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

# Optional: secret of the Keycloak client algorithm stores use. When set, HQ creates
# that client in Keycloak if it does not exist yet.
STORE_ADMIN_CLIENT_SECRET_ENV_VAR = "KEYCLOAK_STORE_ADMIN_CLIENT_SECRET"
# Optional: names of the Keycloak client algorithm stores use, and of the client HQ
# uses to read approved algorithms from algorithm stores
STORE_ADMIN_CLIENT_ENV_VAR = "KEYCLOAK_STORE_ADMIN_CLIENT"
HQ_STORE_READER_CLIENT_ENV_VAR = "KEYCLOAK_HQ_STORE_READER_CLIENT"

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
