from pathlib import Path

from vantage6.common.globals import APPNAME

#
#   INSTALLATION SETTINGS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent

DATA_FOLDER = PACKAGE_FOLDER / APPNAME / "server" / "_data"

SERVER_MODULE_NAME = APPNAME + "-server"

#
#   RUNTIME SETTINGS
#

# Expiretime of JWT tokens
ACCESS_TOKEN_EXPIRES_HOURS = 6

# minimum validity of JWT Tokens in seconds
MIN_TOKEN_VALIDITY_SECONDS = 1800

# Expiration time of refresh tokens
REFRESH_TOKENS_EXPIRE_HOURS = 48

# Minimum time in seconds that a refresh token must be valid *longer than* the
# access token. This is to prevent the access token from expiring before the
# refresh token.
MIN_REFRESH_TOKEN_EXPIRY_DELTA = 1

# Where the resources modules have to be loaded from
RESOURCES_PATH = "vantage6.server.resource"

# Which resources should be initialized. These names correspond to the
# file-names in the resource directory
RESOURCES = [
    "node",
    "collaboration",
    "organization",
    "task",
    "run",
    "token",
    "user",
    "version",
    "recover",
    "role",
    "rule",
    "health",
    "vpn",
    "port",
    "event",
    "algorithm_store",
    "study",
    "session",
]

# Super user information. This user is only created if it is not in the
# database yet at startup time.
SUPER_USER_INFO = {"username": "root", "password": "root"}

# default time that token is valid in minutes
DEFAULT_EMAILED_TOKEN_VALIDITY_MINUTES = 60

# default password policies
DEFAULT_MAX_FAILED_ATTEMPTS = 5
DEFAULT_INACTIVATION_MINUTES = 15
DEFAULT_BETWEEN_USER_EMAILS_MINUTES = 60
