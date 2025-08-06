import logging
import os
from dataclasses import dataclass

from keycloak import KeycloakAdmin, KeycloakOpenID

from vantage6.backend.common.globals import RequiredServerEnvVars
from vantage6.backend.common.resource.error_handling import BadRequestError

log = logging.getLogger(__name__)


@dataclass
class KeycloakServiceAccount:
    """Details about a service account in Keycloak"""

    client_id: str
    client_secret: str
    user_id: str


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
    try:
        keycloak_admin: KeycloakAdmin = get_keycloak_admin_client()
        keycloak_id = keycloak_admin.get_user_id(username)
    except Exception as exc:
        log.exception(exc)
        raise BadRequestError("Could not retrieve user from Keycloak") from exc

    if keycloak_id is None:
        raise BadRequestError("User does not exist in Keycloak")
    return keycloak_id


def create_service_account_in_keycloak(
    client_name: str, is_node: bool = True
) -> KeycloakServiceAccount:
    """
    Create a service account in Keycloak
    """
    try:
        keycloak_admin: KeycloakAdmin = get_keycloak_admin_client()
        client_id = keycloak_admin.create_client(
            {
                "clientId": client_name,
                "publicClient": False,
                "enabled": True,
                "serviceAccountsEnabled": True,
                "standardFlowEnabled": False,
                "protocolMappers": [
                    {
                        "name": "vantage6_client_type",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-hardcoded-claim-mapper",
                        "config": {
                            "claim.name": "vantage6_client_type",
                            "claim.value": "node" if is_node else "user",
                            "access.token.claim": True,
                        },
                    }
                ],
            }
        )
        user_id = keycloak_admin.get_user_id(f"service-account-{client_name}")
        secret = keycloak_admin.get_client_secrets(client_id)
    except Exception as exc:
        log.exception(exc)
        raise BadRequestError(
            f"Could not create service account '{client_name}' in Keycloak"
        ) from exc
    return KeycloakServiceAccount(client_id, secret["value"], user_id)


def get_service_account_in_keycloak(client_name: str) -> KeycloakServiceAccount:
    """
    Get a service account in Keycloak
    """
    keycloak_admin: KeycloakAdmin = get_keycloak_admin_client()
    client_id = keycloak_admin.get_client_id(client_name)
    user_id = keycloak_admin.get_user_id(f"service-account-{client_name}")
    secret = keycloak_admin.get_client_secrets(client_id)
    return KeycloakServiceAccount(client_id, secret["value"], user_id)


def delete_service_account_in_keycloak(client_id: str) -> None:
    """
    Delete a service account in Keycloak
    """
    try:
        keycloak_admin: KeycloakAdmin = get_keycloak_admin_client()
        keycloak_admin.delete_client(client_id)
    except Exception as exc:
        log.exception(exc)
        raise BadRequestError(
            "Service account '{client_id}' could not be deleted from Keycloak"
        ) from exc
