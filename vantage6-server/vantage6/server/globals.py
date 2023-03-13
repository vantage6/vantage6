import datetime

from pathlib import Path

from vantage6.common.globals import APPNAME

#
#   INSTALLATION SETTINGS
#
PACKAGE_FOLDER = Path(__file__).parent.parent.parent

DATA_FOLDER = PACKAGE_FOLDER / APPNAME / "server" / "_data"

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

# Expiretime of JWT token in a test environment
JWT_TEST_ACCESS_TOKEN_EXPIRES = datetime.timedelta(days=1)

# Which resources should be initialized. These names correspond to the
# file-names in the resource directory
RESOURCES = ['node', 'collaboration', 'organization', 'task', 'result',
             'token', 'user', 'version', 'recover', 'role',
             'rule', 'health', 'vpn', 'port', 'event']

# Super user information. This user is only created if it is not in the
# database yet at startup time.
SUPER_USER_INFO = {
    "username": "root",
    "password": "root"
}

# default support email address
DEFAULT_SUPPORT_EMAIL_ADDRESS = 'support@vantage6.ai'

# default time that token is valid in minutes
DEFAULT_EMAILED_TOKEN_VALIDITY_MINUTES = 60
