from pathlib import Path


STRING_ENCODING = "utf-8"

#
#   INSTALLATION SETTINGS
#
PACAKAGE_FOLDER = Path(__file__).parent.parent.parent

APPNAME = "vantage6"

with open(Path(PACAKAGE_FOLDER) / APPNAME / "VERSION") as f:
    VERSION = f.read()