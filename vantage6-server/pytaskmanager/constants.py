from pathlib import Path

#
#   NODE SETTINGS
#
DEFAULT_NODE_SYSTEM_FOLDERS = False

DEFAULT_NODE_ENVIRONMENT = "application"

#
#   SERVER SETTINGS
#
DEFAULT_SERVER_SYSTEM_FOLDERS = True

DEFAULT_SERVER_ENVIRONMENT = "prod"

#
#   INSTALLATION SETTINGS
#
PACAKAGE_FOLDER = str(Path(__file__).parent.parent)

APPNAME = "pytaskmanager"