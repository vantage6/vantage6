from pathlib import Path

#
#   PACKAGE GLOBALS
#
STRING_ENCODING = "utf-8"

DEFAULT_ENVIRONMENT = "application"

APPNAME = "vantage6"

#
#   COMMON GLOBALS
#
PACAKAGE_FOLDER = Path(__file__).parent.parent.parent

with open(Path(PACAKAGE_FOLDER) / APPNAME / "common" / "VERSION") as f:
    VERSION = f.read()
