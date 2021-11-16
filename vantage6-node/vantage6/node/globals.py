from pathlib import Path
from vantage6.common.globals import APPNAME

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


#
#    VPN CONFIGURATION RELATED CONSTANTS
#
# TODO move part of these constants elsewhere?! Or make context?
VPN_CLIENT_IMAGE = 'harbor2.vantage6.ai/infrastructure/vpn-client'
NETWORK_CONFIG_IMAGE = 'harbor2.vantage6.ai/infrastructure/vpn-configurator'
MAX_CHECK_VPN_ATTEMPTS = 60   # max attempts to obtain VPN IP (1 second apart)
FREE_PORT_RANGE = range(49152, 65535)
DEFAULT_ALGO_VPN_PORT = '8888'  # default VPN port for algorithm container
