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

# constants for retrying node login
SLEEP_BTWN_NODE_LOGIN_TRIES = 10  # retry every 10s
TIME_LIMIT_RETRY_CONNECT_NODE = 60 * 60 * 24 * 7  # i.e. 1 week

# constant for waiting for the initial websocket connection
TIME_LIMIT_INITIAL_CONNECTION_WEBSOCKET = 60

# constants for retrying task start due to a temporary error
TASK_START_RETRIES = 3

# The time that a k8s needs to report any state. In case of a timeout, the
# task is considered failed. Note that the Job will try to restart the container
# at most `TASK_START_RETRIES` times (within this timeout).
TASK_START_TIMEOUT_SECONDS = 60 * 5  # 5 minutes

# Environment variables that should be set in the Dockerfile and that may not
# be overwritten by the user.
ENV_VARS_NOT_SETTABLE_BY_NODE = ["PKG_NAME"]

# default policies
DEFAULT_REQUIRE_ALGO_IMAGE_PULL = True

# Mount paths within the algorithm containers. Algorithms containers are run as
# jobs in the Kubernetes cluster.
# TODO v5+ we might consider using different paths for this to avoid conflicts with
# the algorithm image contents. Maybe e.g. `/app/vantage6/task/input` etc?
JOB_POD_INPUT_PATH = "/app/input"
JOB_POD_OUTPUT_PATH = "/app/output"
JOB_POD_TOKEN_PATH = "/app/token"
JOB_POD_SESSION_FOLDER_PATH = "/app/session"

# The mount location of the tasks files, databases and kube config in the node
# container.
TASK_FILES_ROOT = "/app/tasks"
DATABASE_BASE_PATH = "/app/databases/"
KUBE_CONFIG_FILE_PATH = "/app/.kube/config"

# Must be consistent with node pod configuration
PROXY_SERVER_HOST = "http://v6proxy-subdomain.vantage6-node.svc.cluster.local"
PROXY_SERVER_PORT = 4567
