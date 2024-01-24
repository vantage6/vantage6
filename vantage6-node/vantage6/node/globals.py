from pathlib import Path
from vantage6.common.globals import APPNAME

#
#   NODE SETTINGS
#
DEFAULT_NODE_SYSTEM_FOLDERS = False

#
#   INSTALLATION SETTINGS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent

NODE_PROXY_SERVER_HOSTNAME = "proxyserver"

DATA_FOLDER = PACKAGE_FOLDER / APPNAME / "_data"

# with open(Path(PACKAGE_FOLDER) / APPNAME / "node" / "VERSION") as f:
#     VERSION = f.read()


# constants for retrying node login
SLEEP_BTWN_NODE_LOGIN_TRIES = 10  # retry every 10s
TIME_LIMIT_RETRY_CONNECT_NODE = 60 * 60 * 24 * 7  # i.e. 1 week

# constant for waiting for the initial websocket connection
TIME_LIMIT_INITIAL_CONNECTION_WEBSOCKET = 60

#
#    VPN CONFIGURATION RELATED CONSTANTS
#
# TODO move part of these constants elsewhere?! Or make context?
VPN_CLIENT_IMAGE = "harbor2.vantage6.ai/infrastructure/vpn-client"
NETWORK_CONFIG_IMAGE = "harbor2.vantage6.ai/infrastructure/vpn-configurator"
ALPINE_IMAGE = "harbor2.vantage6.ai/infrastructure/alpine"
MAX_CHECK_VPN_ATTEMPTS = 60  # max attempts to obtain VPN IP (1 second apart)
FREE_PORT_RANGE = range(49152, 65535)
DEFAULT_ALGO_VPN_PORT = "8888"  # default VPN port for algorithm container

#
#   SSH TUNNEL RELATED CONSTANTS
#
SSH_TUNNEL_IMAGE = "harbor2.vantage6.ai/infrastructure/ssh-tunnel"

#
#   SQUID RELATED CONSTANTS
#
SQUID_IMAGE = "harbor2.vantage6.ai/infrastructure/squid"

# Environment variables that should be set in the Dockerfile and that may not
# be overwritten by the user.
ENV_VARS_NOT_SETTABLE_BY_NODE = ["PKG_NAME"]
