import datetime

from pathlib import Path

from vantage6.common.globals import APPNAME

#
#   INSTALLATION SETTINGS
#
PACAKAGE_FOLDER = Path(__file__).parent.parent.parent

DATA_FOLDER = PACAKAGE_FOLDER / APPNAME / "server" / "_data"

#
#   RUNTIME SETTINGS
#

# Expiretime of JWT tokens
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=6)

# Expiretime of JWT token in a test environment
JWT_TEST_ACCESS_TOKEN_EXPIRES = datetime.timedelta(days=1)

# Which resources should be initialized. These names correspond to the
# file-names in the resource directory
RESOURCES = ['node', 'collaboration', 'organization', 'task', 'result',
             'token', 'user', 'version', 'recover', 'role',
             'rule', 'health', 'vpn', 'port']

# Super user information. This user is only created if it is not in the
# database yet at startup time.
SUPER_USER_INFO = {
    "username": "root",
    "password": "root"
}

# Whenever the refresh tokens should expire. Note that setting this to true
# would mean that nodes will disconnect after some time
REFRESH_TOKENS_EXPIRE = False

# default support email address
DEFAULT_SUPPORT_EMAIL_ADDRESS = 'support@vantage6.ai'

# default time that token is valid in minutes
DEFAULT_EMAILED_TOKEN_VALIDITY_MINUTES = 60