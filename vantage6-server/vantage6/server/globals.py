from pathlib import Path
from vantage6.common.globals import APPNAME, STRING_ENCODING

#
#   SERVER SETTINGS
#
DEFAULT_SERVER_SYSTEM_FOLDERS = True

DEFAULT_SERVER_ENVIRONMENT = "prod"


#
#   INSTALLATION SETTINGS
#
PACAKAGE_FOLDER = Path(__file__).parent.parent.parent

DATA_FOLDER = PACAKAGE_FOLDER / APPNAME / "server" / "_data"

with open(Path(PACAKAGE_FOLDER) / APPNAME / "server" / "VERSION") as f:
    VERSION = f.read()