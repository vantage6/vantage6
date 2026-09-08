from enum import Enum
from pathlib import Path

#
#   PACKAGE GLOBALS
#
STRING_ENCODING = "utf-8"

APPNAME = "vantage6"

MAIN_VERSION_NAME = "cotopaxi"

DEFAULT_DOCKER_REGISTRY = "ghcr.io/vantage6"

DEFAULT_NODE_IMAGE = f"infrastructure/node:{MAIN_VERSION_NAME}"

DEFAULT_NODE_IMAGE_WO_TAG = "infrastructure/node"

DEFAULT_SERVER_IMAGE = f"infrastructure/server:{MAIN_VERSION_NAME}"

DEFAULT_UI_IMAGE = f"infrastructure/ui:{MAIN_VERSION_NAME}"

DEFAULT_ALGO_STORE_IMAGE = f"infrastructure/algorithm-store:{MAIN_VERSION_NAME}"

#
#   COMMON GLOBALS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent

VPN_CONFIG_FILE = "vpn-config.ovpn.conf"

DATABASE_TYPES = ["csv", "parquet", "sql", "sparql", "excel", "other"]
# Default when database.mount_mode is omitted. Keep "copy" unless default "ro"
# behavior for non-file databases is explicitly handled.
DEFAULT_DB_MOUNT_MODE = "copy"

PING_INTERVAL_SECONDS = 60

# start trying to refresh the JWT token of the node 10 minutes before it
# expires.
NODE_CLIENT_REFRESH_BEFORE_EXPIRES_SECONDS = 600

# The basics image can be used (mainly by the UI) to collect column names
BASIC_PROCESSING_IMAGE = "ghcr.io/vantage6/algorithm-basics:latest"

# Character to replace '=' with in encoded environment variables
ENV_VAR_EQUALS_REPLACEMENT = "!"

# default API path (for server and algorithm store)
DEFAULT_API_PATH = "/api"
DEFAULT_PROMETHEUS_EXPORTER_PORT = 7603

# Maximum interval to wait for requesting results from a task
MAX_INTERVAL = 300

# Constant multiplier to make interval for requesting results from a task progressively longer
INTERVAL_MULTIPLIER = 1.5

# Default timeout for requests to the server
REQUEST_TIMEOUT = 300

# In-memory buffer size when reading a stream (downloads, file reads).
DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1MB

# Wire-level chunk size for HTTP Transfer-Encoding: chunked uploads of run data
# and encrypted streams. Must stay well below the server-side per-part limit
# (``MAX_CHUNKED_INPUT_PART`` here, ``--chunked-input-limit`` on uwsgi, whose
# built-in default is 1 MiB): uwsgi counts each part plus its 2-byte CRLF
# framing against that limit, so the largest usable part is limit - 2 and
# anything bigger fails with ``IOError: unable to receive chunked part``.
HTTP_UPLOAD_CHUNK_SIZE = 256 * 1024  # 256 KiB

# Per-part cap (in bytes) that `v6 server start` passes to uwsgi as
# ``--chunked-input-limit`` (server.sh sets the same value inline).
# Deliberately much larger than ``HTTP_UPLOAD_CHUNK_SIZE`` so the friendly
# client always has headroom, and small enough to reject obviously hostile
# bodies before they consume server memory.
MAX_CHUNKED_INPUT_PART = 16 * 1024 * 1024  # 16 MiB


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
    ALLOW_BASICS_ALGORITHM = "allow_basics_algorithm"
    REQUIRE_ALGORITHM_PULL = "require_algorithm_pull"


class Ports(int, Enum):
    HTTP = 80
    HTTPS = 443
    DEV_SERVER = 7601
    DEV_UI = 7600
    DEV_ALGO_STORE = 7602


class AuthStatus(str, Enum):
    """Enum containing the different statuses of the authenticable (node/user)"""

    ONLINE = "online"
    OFFLINE = "offline"
