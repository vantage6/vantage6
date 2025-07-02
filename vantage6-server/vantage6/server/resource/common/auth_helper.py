import os
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection

from vantage6.backend.common.globals import RequiredServerEnvVars


def getKeyCloakAdminClient():
    keycloak_openid = KeycloakOpenIDConnection(
        server_url=os.environ.get(RequiredServerEnvVars.KEYCLOAK_URL.value),
        username=os.environ.get(RequiredServerEnvVars.KEYCLOAK_ADMIN_USERNAME.value),
        password=os.environ.get(RequiredServerEnvVars.KEYCLOAK_ADMIN_PASSWORD.value),
        client_id=os.environ.get(RequiredServerEnvVars.KEYCLOAK_ADMIN_CLIENT.value),
        realm_name=os.environ.get(RequiredServerEnvVars.KEYCLOAK_REALM.value),
        client_secret_key=os.environ.get(
            RequiredServerEnvVars.KEYCLOAK_ADMIN_CLIENT_SECRET.value
        ),
    )
    return KeycloakAdmin(connection=keycloak_openid)
