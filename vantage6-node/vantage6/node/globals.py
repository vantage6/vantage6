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

# TODO Check and remove
# HCR: This constants is not being used, as well as the other defined in cli/globals.py
# NODE_PROXY_SERVER_HOSTNAME = "proxyserver"

# Timeout in seconds of the K8S event-stream watch used by the container manager.
# This is the maximum amount of time the container manager will wait
# for a terminal event (job pod created successfuly, creation failed, etc).
# The container manager will wait again (for up to K8S_EVENT_STREAM_LOOP_TIMEOUT seconds)
# for events if the timeout is caused by a long image pull (massive image or slow connection)
# so this parameter doesn't have a significant impact on the container manager
# behaviour.
K8S_EVENT_STREAM_LOOP_TIMEOUT = 120

DATA_FOLDER = PACKAGE_FOLDER / APPNAME / "_data"

# constants for retrying node login
SLEEP_BTWN_NODE_LOGIN_TRIES = 10  # retry every 10s
TIME_LIMIT_RETRY_CONNECT_NODE = 60 * 60 * 24 * 7  # i.e. 1 week

# constant for waiting for the initial websocket connection
TIME_LIMIT_INITIAL_CONNECTION_WEBSOCKET = 60

# constants for retrying task start due to a temporary error
TASK_START_RETRIES = 3

# Environment variables that should be set in the Dockerfile and that may not
# be overwritten by the user.
ENV_VARS_NOT_SETTABLE_BY_NODE = ["PKG_NAME"]

# default policies
DEFAULT_REQUIRE_ALGO_IMAGE_PULL = True

# Mount paths within the algorithm containers. Algorithms containers are run as
# jobs in the Kubernetes cluster.
JOB_POD_INPUT_PATH = "/app/vantage6/task/input"
JOB_POD_OUTPUT_PATH = "/app/vantage6/task/output"
JOB_POD_SESSION_FOLDER_PATH = "/app/vantage6/task/session"

# The mount location of the tasks files, databases and kube config in the node
# container.
TASK_FILES_ROOT = "/app/tasks"
DATABASE_BASE_PATH = "/app/databases/"

# Default proxy server port. It may be changed when starting the proxy if
# the port is already in use
DEFAULT_PROXY_SERVER_PORT = 7654
