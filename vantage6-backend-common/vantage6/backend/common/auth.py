import logging
import os
from dataclasses import dataclass

from keycloak import KeycloakAdmin, KeycloakError, KeycloakOpenID

from vantage6.common.globals import (
    HQ_AUDIENCE_SCOPE,
    HQ_TOKEN_AUDIENCE,
    STORE_AUDIENCE_SCOPE,
    STORE_TOKEN_AUDIENCE,
)

from vantage6.backend.common.globals import RequiredBackendEnvVars
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
        server_url=os.environ.get(RequiredBackendEnvVars.KEYCLOAK_URL.value),
        client_id=os.environ.get(RequiredBackendEnvVars.KEYCLOAK_ADMIN_CLIENT.value),
        realm_name=os.environ.get(RequiredBackendEnvVars.KEYCLOAK_REALM.value),
        client_secret_key=os.environ.get(
            RequiredBackendEnvVars.KEYCLOAK_ADMIN_CLIENT_SECRET.value
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
        server_url=os.environ.get(RequiredBackendEnvVars.KEYCLOAK_URL.value),
        realm_name=os.environ.get(RequiredBackendEnvVars.KEYCLOAK_REALM.value),
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
        log.exception("Could not retrieve user from Keycloak")
        raise BadRequestError("Could not retrieve user from Keycloak") from exc

    if keycloak_id is None:
        raise BadRequestError("User does not exist in Keycloak")
    return keycloak_id


def get_user_from_keycloak(keycloak_user_id: str) -> dict:
    """
    Get user data from Keycloak including attributes.

    Parameters
    ----------
    keycloak_user_id : str
        The Keycloak user ID

    Returns
    -------
    dict
        User representation from Keycloak including attributes

    Raises
    ------
    BadRequestError
        If the user could not be retrieved from Keycloak
    """
    try:
        keycloak_admin: KeycloakAdmin = get_keycloak_admin_client()
        user_data = keycloak_admin.get_user(keycloak_user_id)
    except Exception as exc:
        log.exception("Could not retrieve user from Keycloak")
        raise BadRequestError("Could not retrieve user from Keycloak") from exc

    if user_data is None:
        raise BadRequestError("User does not exist in Keycloak")
    return user_data


def get_organization_id_from_keycloak(keycloak_user_id: str) -> int | None:
    """
    Get organization_id from Keycloak user attributes.

    Parameters
    ----------
    keycloak_user_id : str
        The Keycloak user ID

    Returns
    -------
    int | None
        Organization ID if found, None otherwise

    Raises
    ------
    BadRequestError
        If the user could not be retrieved from Keycloak
    """
    try:
        user_data = get_user_from_keycloak(keycloak_user_id)
        attributes = user_data.get("attributes", {})
        organization_id_list = attributes.get("organization_id", [])

        if organization_id_list and len(organization_id_list) > 0:
            # Keycloak attributes are stored as lists of strings
            return int(organization_id_list[0])
        return None
    except (ValueError, TypeError) as exc:
        log.warning(
            "Could not parse organization_id from Keycloak attributes for user %s: %s",
            keycloak_user_id,
            exc,
        )
        return None


def create_service_account_in_keycloak(
    client_name: str, is_node: bool = True
) -> KeycloakServiceAccount:
    """
    Create a service account in Keycloak
    """
    try:
        keycloak_admin: KeycloakAdmin = get_keycloak_admin_client()
        client_id = keycloak_admin.create_client(
            _service_account_client(client_name, "node" if is_node else "user")
        )
        # service accounts request a token per audience: one for HQ, one for stores
        _add_optional_scopes(
            keycloak_admin, client_id, [HQ_AUDIENCE_SCOPE, STORE_AUDIENCE_SCOPE]
        )
        user_id = keycloak_admin.get_user_id(f"service-account-{client_name}")
        secret = keycloak_admin.get_client_secrets(client_id)
    except Exception as exc:
        log.exception("Could not create service account '%s' in Keycloak", client_name)
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
        log.exception("Could not delete service account '%s' from Keycloak", client_id)
        raise BadRequestError(
            f"Service account '{client_id}' could not be deleted from Keycloak"
        ) from exc


def _client_type_mapper(client_type: str) -> dict:
    """Protocol mapper that sets the `vantage6_client_type` claim"""
    return {
        "name": "vantage6_client_type",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-hardcoded-claim-mapper",
        "config": {
            "claim.name": "vantage6_client_type",
            "claim.value": client_type,
            "access.token.claim": True,
        },
    }


def _service_account_client(client_name: str, client_type: str) -> dict:
    """
    Representation of a confidential client that only uses its service account. Its
    tokens carry `client_type` as `vantage6_client_type`.
    """
    return {
        "clientId": client_name,
        "publicClient": False,
        "enabled": True,
        "serviceAccountsEnabled": True,
        "standardFlowEnabled": False,
        "protocolMappers": [_client_type_mapper(client_type)],
    }


def _get_client_scope_ids(keycloak_admin: KeycloakAdmin) -> dict[str, str]:
    return {scope["name"]: scope["id"] for scope in keycloak_admin.get_client_scopes()}


def _add_optional_scopes(
    keycloak_admin: KeycloakAdmin, client_id: str, scope_names: list[str]
) -> None:
    scope_ids = _get_client_scope_ids(keycloak_admin)
    present = {
        scope["name"]
        for scope in keycloak_admin.get_client_optional_client_scopes(client_id)
    }
    for name in scope_names:
        if name not in present:
            keycloak_admin.add_client_optional_client_scope(
                client_id, scope_ids[name], {}
            )


def _add_default_scope(
    keycloak_admin: KeycloakAdmin, client_id: str, scope_name: str
) -> None:
    present = {
        scope["name"]
        for scope in keycloak_admin.get_client_default_client_scopes(client_id)
    }
    if scope_name not in present:
        scope_id = _get_client_scope_ids(keycloak_admin)[scope_name]
        keycloak_admin.add_client_default_client_scope(client_id, scope_id, {})


def _ensure_audience_scopes(keycloak_admin: KeycloakAdmin) -> None:
    """
    Create the client scopes that add the HQ or store audience to a token.

    These are created here rather than in the Keycloak realm import: when an imported
    realm defines any client scopes, Keycloak does not create its built-in scopes
    (e.g. `basic`, `profile`, `roles`, `web-origins`), so tokens would lack claims
    such as `sub`. Copying those built-in scopes into the realm import would tie it to
    the Keycloak version.
    """
    existing = _get_client_scope_ids(keycloak_admin)
    for scope_name, audience in [
        (HQ_AUDIENCE_SCOPE, HQ_TOKEN_AUDIENCE),
        (STORE_AUDIENCE_SCOPE, STORE_TOKEN_AUDIENCE),
    ]:
        if scope_name in existing:
            continue
        keycloak_admin.create_client_scope(
            {
                "name": scope_name,
                "protocol": "openid-connect",
                "attributes": {"include.in.token.scope": "false"},
                "protocolMappers": [
                    {
                        "name": f"{audience}-audience",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-audience-mapper",
                        "config": {
                            "included.custom.audience": audience,
                            "access.token.claim": "true",
                            "id.token.claim": "false",
                        },
                    }
                ],
            }
        )


def ensure_keycloak_token_setup(
    public_client: str, hq_store_reader_client: str
) -> None:
    """
    Make sure the Keycloak realm issues separate tokens for HQ and for algorithm
    stores. It is safe to run on every start.

    Parameters
    ----------
    public_client : str
        Client users log in with
    hq_store_reader_client : str
        Client HQ uses to read approved algorithms from algorithm stores as itself
    """
    keycloak_admin: KeycloakAdmin = get_keycloak_admin_client()
    _ensure_audience_scopes(keycloak_admin)

    public_client_id = keycloak_admin.get_client_id(public_client)
    if public_client_id is None:
        log.warning("Keycloak client '%s' not found", public_client)
    else:
        # Users log in for both audiences and then get a token per audience
        _add_optional_scopes(
            keycloak_admin, public_client_id, [HQ_AUDIENCE_SCOPE, STORE_AUDIENCE_SCOPE]
        )

    if keycloak_admin.get_client_id(hq_store_reader_client) is None:
        log.info("Creating Keycloak client '%s'", hq_store_reader_client)
        keycloak_admin.create_client(
            _service_account_client(hq_store_reader_client, "hq")
        )
    _add_default_scope(
        keycloak_admin,
        keycloak_admin.get_client_id(hq_store_reader_client),
        STORE_AUDIENCE_SCOPE,
    )


def get_email_for_keycloak_id(keycloak_id: str) -> str | None:
    """
    Get the email for a keycloak id

    Parameters
    ----------
    keycloak_id: str
        The keycloak id of the user

    Returns
    -------
    str | None:
        The email address of the user or None if it was not found
    """
    try:
        keycloak_admin: KeycloakAdmin = get_keycloak_admin_client()
        user_details = keycloak_admin.get_user(keycloak_id)
        return user_details["email"]
    except KeycloakError as exc:
        log.error(exc)
        return None
