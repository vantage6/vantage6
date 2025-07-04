import os
from keycloak import KeycloakAdmin, KeycloakOpenID

from vantage6.backend.common.globals import RequiredServerEnvVars


def getKeyCloakAdminClient():
    # Use KeycloakOpenID for service account authentication
    keycloak_openid = KeycloakOpenID(
        server_url=os.environ.get(RequiredServerEnvVars.KEYCLOAK_URL.value),
        client_id=os.environ.get(RequiredServerEnvVars.KEYCLOAK_ADMIN_CLIENT.value),
        realm_name=os.environ.get(RequiredServerEnvVars.KEYCLOAK_REALM.value),
        client_secret_key=os.environ.get(
            RequiredServerEnvVars.KEYCLOAK_ADMIN_CLIENT_SECRET.value
        ),
    )

    # Get token using client credentials (service account) flow
    token = keycloak_openid.token(grant_type="client_credentials")

    # Create KeycloakAdmin with the service account token
    keycloak_admin = KeycloakAdmin(
        server_url=os.environ.get(RequiredServerEnvVars.KEYCLOAK_URL.value),
        realm_name=os.environ.get(RequiredServerEnvVars.KEYCLOAK_REALM.value),
        token=token,
        verify=True,
    )

    return keycloak_admin
