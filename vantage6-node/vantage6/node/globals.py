from pathlib import Path
from vantage6.common.globals import (
    APPNAME,
    STRING_ENCODING
)


#
#   NODE SETTINGS
#
DEFAULT_NODE_SYSTEM_FOLDERS = False

DEFAULT_NODE_ENVIRONMENT = "application"


#
#   INSTALLATION SETTINGS
#
PACAKAGE_FOLDER = Path(__file__).parent.parent.parent

NODE_PROXY_SERVER_HOSTNAME = "proxyserver"

DATA_FOLDER = PACAKAGE_FOLDER / APPNAME / "_data"

# with open(Path(PACAKAGE_FOLDER) / APPNAME / "node" / "VERSION") as f:
#     VERSION = f.read()