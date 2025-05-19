from keycloak import KeycloakAdmin, KeycloakOpenIDConnection


def getKeyCloakAdminClient():
    keycloak_openid = KeycloakOpenIDConnection(
        server_url="http://vantage6-auth-keycloak.default.svc.cluster.local",
        username="admin",
        password="admin",
        client_id="admin-client",
        realm_name="vantage6",
        client_secret_key="myadminsecret",
    )
    return KeycloakAdmin(connection=keycloak_openid)
