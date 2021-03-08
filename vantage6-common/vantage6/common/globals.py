from pathlib import Path

#
#   PACKAGE GLOBALS
#
STRING_ENCODING = "utf-8"

DEFAULT_ENVIRONMENT = "application"

APPNAME = "vantage6"

DEFAULT_DOCKER_REGISTRY = "harbor2.vantage6.ai"

DEFAULT_NODE_IMAGE = "infrastructure/node:harukas"

DEFAULT_SERVER_IMAGE = "infrastructure/server:harukas"


#
#   COMMON GLOBALS
#
PACAKAGE_FOLDER = Path(__file__).parent.parent.parent
