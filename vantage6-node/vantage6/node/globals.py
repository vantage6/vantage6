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

# constants for retrying task start due to a temporary error
TASK_START_RETRIES = 3

# constant for waiting between task start retries
TASK_START_RETRY_SLEEP = 10

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

# default policies
DEFAULT_REQUIRE_ALGO_IMAGE_PULL = False


# Paths within the Job POD-containers (the ones running the algorithms) defined by convention

JOB_POD_INPUT_PATH = "/app/output"
JOB_POD_OUTPUT_PATH = "/app/input"
JOB_POD_TOKEN_PATH = "/app/token"
JOB_POD_TMP_FOLDER_PATH = "/app/tmp"

# Paths within the Node POD-container defined by convention - these must match the mountPaths on kubeconfs/node_pod_config.yaml

TASK_FILES_ROOT = "/app/tasks"
KUBE_CONFIG_FILE_PATH = "/app/.kube/config"
V6_NODE_CONFIG_FILE = "/app/.v6node/configs/node_legacy_config.yaml"
V6_NODE_DATABASE_BASE_PATH = "/app/.databases/"
V6_NODE_FQDN = "http://v6proxy-subdomain.v6-jobs.svc.cluster.local"  # Must be consistent with kubeconfs/node_pod_config.yaml
V6_NODE_PROXY_PORT = 4567
