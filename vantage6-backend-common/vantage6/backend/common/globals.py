from vantage6.common.enum import StrEnumBase

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

# Default name of the Keycloak client HQ uses to read approved algorithms from
# algorithm stores as itself
DEFAULT_HQ_STORE_READER_KEYCLOAK_CLIENT = "hq-store-reader-client"
# Default name of the Keycloak client algorithm stores use to look up users
DEFAULT_STORE_ADMIN_KEYCLOAK_CLIENT = "store-admin-client"
# Names of HQ's Keycloak clients in realms created before they were named after HQ.
# HQ renames them at startup.
LEGACY_HQ_ADMIN_KEYCLOAK_CLIENT = "backend-admin-client"
LEGACY_HQ_PUBLIC_KEYCLOAK_CLIENT = "public_client"


class RequiredBackendEnvVars(StrEnumBase):
    """Enum containing the required backend environment variables"""

    KEYCLOAK_URL = "KEYCLOAK_URL"
    KEYCLOAK_REALM = "KEYCLOAK_REALM"
    KEYCLOAK_ADMIN_USERNAME = "KEYCLOAK_ADMIN_USERNAME"
    KEYCLOAK_ADMIN_PASSWORD = "KEYCLOAK_ADMIN_PASSWORD"
    KEYCLOAK_ADMIN_CLIENT = "KEYCLOAK_ADMIN_CLIENT"
    KEYCLOAK_ADMIN_CLIENT_SECRET = "KEYCLOAK_ADMIN_CLIENT_SECRET"
