from pathlib import Path
from vantage6.common.globals import (
    APPNAME,
    STRING_ENCODING
)

#
#   SERVER SETTINGS
#
DEFAULT_SERVER_SYSTEM_FOLDERS = True

DEFAULT_SERVER_ENVIRONMENT = "prod"

#
#   NODE SETTINGS
#
DEFAULT_NODE_SYSTEM_FOLDERS = False

DEFAULT_NODE_ENVIRONMENT = "application"


#
#   INSTALLATION SETTINGS
#
PACAKAGE_FOLDER = Path(__file__).parent.parent.parent

# FIXME BvB 22-06-28 think this is also defined in the node globals, and this
# one appears not to be used
NODE_PROXY_SERVER_HOSTNAME = "proxyserver"

DATA_FOLDER = PACAKAGE_FOLDER / APPNAME / "_data"

# with open(Path(PACAKAGE_FOLDER) / APPNAME / "cli" / "VERSION") as f:
#     VERSION = f.read()

# Maximum time to start up RabbitMQ in seconds
RABBIT_TIMEOUT = 300
