import os
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection

from vantage6.backend.common.globals import RequiredServerEnvVars


def getKeyCloakAdminClient():
    keycloak_openid = KeycloakOpenIDConnection(
        server_url=os.environ.get(RequiredServerEnvVars.KEYCLOAK_URL.value),
        username="admin",
        password="admin",
        client_id="admin-client",
        realm_name="vantage6",
        client_secret_key="myadminsecret",
    )
    return KeycloakAdmin(connection=keycloak_openid)
