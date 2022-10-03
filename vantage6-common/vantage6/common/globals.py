from pathlib import Path

#
#   PACKAGE GLOBALS
#
STRING_ENCODING = "utf-8"

DEFAULT_ENVIRONMENT = "application"

APPNAME = "vantage6"

DEFAULT_DOCKER_REGISTRY = "harbor2.vantage6.ai"

DEFAULT_NODE_IMAGE = "infrastructure/node:petronas"

DEFAULT_SERVER_IMAGE = "infrastructure/server:petronas"


#
#   COMMON GLOBALS
#
PACAKAGE_FOLDER = Path(__file__).parent.parent.parent

VPN_CONFIG_FILE = 'vpn-config.ovpn.conf'
