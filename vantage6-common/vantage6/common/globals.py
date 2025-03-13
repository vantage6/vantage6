from enum import Enum
from pathlib import Path

#
#   PACKAGE GLOBALS
#
STRING_ENCODING = "utf-8"

APPNAME = "vantage6"

MAIN_VERSION_NAME = "cotopaxi"

DEFAULT_DOCKER_REGISTRY = "harbor2.vantage6.ai"

DEFAULT_NODE_IMAGE = f"infrastructure/node:{MAIN_VERSION_NAME}"

DEFAULT_NODE_IMAGE_WO_TAG = "infrastructure/node"

DEFAULT_SERVER_IMAGE = f"infrastructure/server:{MAIN_VERSION_NAME}"

DEFAULT_UI_IMAGE = f"infrastructure/ui:{MAIN_VERSION_NAME}"

DEFAULT_ALGO_STORE_IMAGE = f"infrastructure/algorithm-store:{MAIN_VERSION_NAME}"

DEFAULT_ALPINE_IMAGE = "infrastructure/alpine:latest"

#
#   COMMON GLOBALS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent

VPN_CONFIG_FILE = "vpn-config.ovpn.conf"

DATABASE_TYPES = ["csv", "parquet", "sql", "sparql", "excel", "other"]

PING_INTERVAL_SECONDS = 60

# start trying to refresh the JWT token of the node 10 minutes before it
# expires.
NODE_CLIENT_REFRESH_BEFORE_EXPIRES_SECONDS = 600

# Character to replace '=' with in encoded environment variables
ENV_VAR_EQUALS_REPLACEMENT = "!"

# default API path (for server and algorithm store)
DEFAULT_API_PATH = "/api"


class InstanceType(str, Enum):
    """The types of instances that can be created."""

    NODE = "node"
    SERVER = "server"
    ALGORITHM_STORE = "algorithm-store"
    UI = "ui"


class NodePolicy(str, Enum):
    """Enum containing the names of the names of the node policies"""

    ALLOWED_ALGORITHMS = "allowed_algorithms"
    ALLOWED_ALGORITHM_STORES = "allowed_algorithm_stores"
    ALLOWED_ORGANIZATIONS = "allowed_organizations"
    ALLOWED_USERS = "allowed_users"
    REQUIRE_ALGORITHM_PULL = "require_algorithm_pull"


class Ports(int, Enum):
    """Enum containing the default ports used by the vantage6 components"""

    HTTP = 80
    HTTPS = 443
    DEV_SERVER = 7601
    DEV_UI = 7600
    DEV_ALGO_STORE = 7602


class ContainerEnvNames(str, Enum):
    """Enum containing the names of the container environment variables"""

    FUNCTION_ACTION = "FUNCTION_ACTION"
    INPUT_FILE = "INPUT_FILE"
    OUTPUT_FILE = "OUTPUT_FILE"
    SESSION_FOLDER = "SESSION_FOLDER"
    SESSION_FILE = "SESSION_FILE"
    HOST = "HOST"
    PORT = "PORT"
    API_PATH = "API_PATH"
    TOKEN_FILE = "TOKEN_FILE"
    DATABASE_URI = "DATABASE_URI"
    DATABASE_TYPE = "DATABASE_TYPE"
    DB_PARAM_PREFIX = "DB_PARAM_"
    USER_REQUESTED_DATAFRAMES = "USER_REQUESTED_DATAFRAMES"
    USER_REQUESTED_DATABASES = "USER_REQUESTED_DATABASES"


class AuthStatus(str, Enum):
    """Enum containing the different statuses of the authenticable (node/user)"""

    ONLINE = "online"
    OFFLINE = "offline"
