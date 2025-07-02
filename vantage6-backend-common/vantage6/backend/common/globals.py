from enum import Enum

# pagination settings
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10

# environment variable name for host URI
HOST_URI_ENV = "HOST_URI_ENV_VAR"

# database attempts setting
MAX_NUMBER_OF_ATTEMPTS = 10
RETRY_DELAY_IN_SECONDS = 30

# default support email address to make users aware of
DEFAULT_SUPPORT_EMAIL_ADDRESS = "support@vantage6.ai"

# default email address used in 'from' header
DEFAULT_EMAIL_FROM_ADDRESS = "noreply@vantage6.ai"


class RequiredServerEnvVars(str, Enum):
    """Enum containing the required server environment variables"""

    KEYCLOAK_URL = "KEYCLOAK_URL"
    KEYCLOAK_REALM = "KEYCLOAK_REALM"
    KEYCLOAK_ADMIN_USERNAME = "KEYCLOAK_ADMIN_USERNAME"
    KEYCLOAK_ADMIN_PASSWORD = "KEYCLOAK_ADMIN_PASSWORD"
    KEYCLOAK_ADMIN_CLIENT = "KEYCLOAK_ADMIN_CLIENT"
    KEYCLOAK_ADMIN_CLIENT_SECRET = "KEYCLOAK_ADMIN_CLIENT_SECRET"
    KEYCLOAK_USER_CLIENT = "KEYCLOAK_USER_CLIENT"
    KEYCLOAK_USER_CLIENT_SECRET = "KEYCLOAK_USER_CLIENT_SECRET"
