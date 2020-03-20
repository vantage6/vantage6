from pathlib import Path


#
#   SERVER SETTINGS
#
DEFAULT_SERVER_SYSTEM_FOLDERS = True

DEFAULT_SERVER_ENVIRONMENT = "prod"

STRING_ENCODING = "utf-8"

#
#   INSTALLATION SETTINGS
#
PACAKAGE_FOLDER = Path(__file__).parent.parent.parent

APPNAME = "vantage6"

DATA_FOLDER = PACAKAGE_FOLDER / APPNAME / "_data"

with open(Path(PACAKAGE_FOLDER) / APPNAME / "VERSION") as f:
    VERSION = f.read()