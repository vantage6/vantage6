from pathlib import Path

#
#   PACKAGE GLOBALS
#
STRING_ENCODING = "utf-8"

DEFAULT_ENVIRONMENT = "application"

APPNAME = "vantage6"

MAIN_VERSION_NAME = "petronas"

DEFAULT_DOCKER_REGISTRY = "harbor2.vantage6.ai"

DEFAULT_NODE_IMAGE = f"infrastructure/node:{MAIN_VERSION_NAME}"

DEFAULT_SERVER_IMAGE = f"infrastructure/server:{MAIN_VERSION_NAME}"


#
#   COMMON GLOBALS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent

VPN_CONFIG_FILE = 'vpn-config.ovpn.conf'

DATABASE_TYPES = ["csv", "parquet", "sql", "sparql", "omop", "excel", "other"]

PING_INTERVAL_SECONDS = 60
