from enum import IntEnum
from pathlib import Path

from vantage6.common.enum import StrEnumBase

#
#   PACKAGE GLOBALS
#
STRING_ENCODING = "utf-8"

APPNAME = "vantage6"

# TODO v5+ change to final v5 name
MAIN_VERSION_NAME = "5"

DEFAULT_DOCKER_REGISTRY = "harbor2.vantage6.ai"

DEFAULT_NODE_IMAGE = f"infrastructure/node:{MAIN_VERSION_NAME}"

DEFAULT_NODE_IMAGE_WO_TAG = "infrastructure/node"

DEFAULT_SERVER_IMAGE = f"infrastructure/server:{MAIN_VERSION_NAME}"

DEFAULT_UI_IMAGE = f"infrastructure/ui:{MAIN_VERSION_NAME}"

DEFAULT_ALGO_STORE_IMAGE = f"infrastructure/algorithm-store:{MAIN_VERSION_NAME}"

DEFAULT_ALPINE_IMAGE = "infrastructure/alpine:latest"

#  CHART GLOBALS
DEFAULT_CHART_REPO = "https://harbor2.vantage6.ai/chartrepo/infrastructure"

#
#   COMMON GLOBALS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent

DATABASE_TYPES = ["csv", "parquet", "sql", "sparql", "excel", "other"]
FILE_BASED_DATABASE_TYPES = ["csv", "parquet", "excel", "other"]
SERVICE_BASED_DATABASE_TYPES = ["sql", "sparql", "other"]

PING_INTERVAL_SECONDS = 60

# Character to replace '=' with in encoded environment variables
ENV_VAR_EQUALS_REPLACEMENT = "!"

# default API path (for server and algorithm store)
DEFAULT_API_PATH = "/api"
DEFAULT_PROMETHEUS_EXPORTER_PORT = 7603

# Maximum interval to wait for requesting results from a task
MAX_INTERVAL = 300

# Constant multiplier to make interval for requesting results from a task progressively
# longer
INTERVAL_MULTIPLIER = 1.5

# keyword for the multiple dataframes in single argument decorator
DATAFRAME_MULTIPLE_KEYWORD = "multiple"
DATAFRAME_WITHIN_GROUP_SEPARATOR = ","
DATAFRAME_BETWEEN_GROUPS_SEPARATOR = ";"

# Default timeout for requests to the server
REQUEST_TIMEOUT = 300

# Default chunk size for streaming inputs and results
DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1MB

# session state file name
SESSION_STATE_FILENAME = "session_state"

# session state file name
SESSION_STATE_FILENAME = "session_state"

# sandbox configuration suffix
SANDBOX_SUFFIX = ".sandbox"

# Localhost addresses
LOCALHOST = "localhost"
HTTP_LOCALHOST = "http://localhost"
LINUX_LOCALHOST = "http://127.0.0.1"


class InstanceType(StrEnumBase):
    """The types of instances that can be created."""

    NODE = "node"
    SERVER = "server"
    ALGORITHM_STORE = "algorithm-store"
    UI = "ui"
    AUTH = "auth"


class NodePolicy(StrEnumBase):
    """Enum containing the names of the names of the node policies"""

    ALLOWED_ALGORITHMS = "allowed_algorithms"
    ALLOWED_ALGORITHM_STORES = "allowed_algorithm_stores"
    ALLOWED_ORGANIZATIONS = "allowed_organizations"
    ALLOWED_USERS = "allowed_users"
    REQUIRE_ALGORITHM_PULL = "require_algorithm_pull"


class NodeConfigKey(StrEnumBase):
    """Enum containing the keys of the node configuration"""

    ENCRYPTION = "encryption"
    ALLOWED_ALGORITHMS = "allowed_algorithms"
    ALLOWED_ORGANIZATIONS = "allowed_orgs"
    ALLOWED_USERS = "allowed_users"
    DATABASE_LABELS = "database_labels"
    DATABASE_TYPES = "database_types"


class Ports(IntEnum):
    """Enum containing the default ports used by the vantage6 components"""

    HTTP = 80
    HTTPS = 443
    DEV_SERVER = 7601
    DEV_UI = 7600
    DEV_ALGO_STORE = 7602
    DEV_AUTH = 8080


class ContainerEnvNames(StrEnumBase):
    """Enum containing the names of the container environment variables"""

    FUNCTION_ACTION = "FUNCTION_ACTION"
    INPUT_FILE = "INPUT_FILE"
    ALGORITHM_METHOD = "ALGORITHM_METHOD"
    OUTPUT_FILE = "OUTPUT_FILE"
    SESSION_FOLDER = "SESSION_FOLDER"
    SESSION_FILE = "SESSION_FILE"
    HOST = "HOST"
    PORT = "PORT"
    API_PATH = "API_PATH"
    CONTAINER_TOKEN = "CONTAINER_TOKEN"
    DATABASE_URI = "DATABASE_URI"
    DATABASE_TYPE = "DATABASE_TYPE"
    DB_PARAM_PREFIX = "DB_PARAM_"
    USER_REQUESTED_DATAFRAMES = "USER_REQUESTED_DATAFRAMES"
    USER_REQUESTED_DATABASES = "USER_REQUESTED_DATABASES"
    TASK_ID = "TASK_ID"
    NODE_ID = "NODE_ID"
    ORGANIZATION_ID = "ORGANIZATION_ID"
    COLLABORATION_ID = "COLLABORATION_ID"


class RequiredNodeEnvVars(StrEnumBase):
    """Enum containing the required node environment variables"""

    V6_API_KEY = "V6_API_KEY"
    V6_NODE_NAME = "V6_NODE_NAME"
    KEYCLOAK_URL = "KEYCLOAK_URL"
    KEYCLOAK_REALM = "KEYCLOAK_REALM"


class AuthStatus(StrEnumBase):
    """Enum containing the different statuses of the authenticable (node/user)"""

    ONLINE = "online"
    OFFLINE = "offline"
