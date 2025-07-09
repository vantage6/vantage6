import os
from keycloak import KeycloakAdmin, KeycloakOpenID

from vantage6.backend.common.globals import RequiredServerEnvVars
from vantage6.backend.common.resource.error_handling import BadRequestError


def _get_admin_token():
    """Get a token for the admin client"""
    keycloak_openid = KeycloakOpenID(
        server_url=os.environ.get(RequiredServerEnvVars.KEYCLOAK_URL.value),
        client_id=os.environ.get(RequiredServerEnvVars.KEYCLOAK_ADMIN_CLIENT.value),
        realm_name=os.environ.get(RequiredServerEnvVars.KEYCLOAK_REALM.value),
        client_secret_key=os.environ.get(
            RequiredServerEnvVars.KEYCLOAK_ADMIN_CLIENT_SECRET.value
        ),
    )

    # Get token using client credentials (service account) flow
    return keycloak_openid.token(grant_type="client_credentials")


def get_keycloak_admin_client():
    """
    Get a KeycloakAdmin client
    """
    token = _get_admin_token()

    # Create KeycloakAdmin with the service account token
    keycloak_admin = KeycloakAdmin(
        server_url=os.environ.get(RequiredServerEnvVars.KEYCLOAK_URL.value),
        realm_name=os.environ.get(RequiredServerEnvVars.KEYCLOAK_REALM.value),
        token=token,
        verify=True,
    )

    return keycloak_admin


def get_keycloak_id_for_user(username: str):
    """
    Get the keycloak id for a user
    """
    keycloak_admin: KeycloakAdmin = get_keycloak_admin_client()
    keycloak_id = keycloak_admin.get_user_id(username)
    if keycloak_id is None:
        raise BadRequestError("User does not exist in Keycloak")
    return keycloak_id
