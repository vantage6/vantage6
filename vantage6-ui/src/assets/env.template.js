// The purpose of this file is to be able to insert environment variables from Docker
(function (window) {
  window["env"] = window["env"] || {};

  // Environment variables
  window["env"]["server_url"] = "${SERVER_URL}";
  window["env"]["api_path"] = "${API_PATH}";
  window["env"]["allowed_algorithm_stores"] = "${ALLOWED_ALGORITHM_STORES}";
  window["env"]["auth_url"] = "${AUTH_URL}";
  window["env"]["keycloak_realm"] = "${KEYCLOAK_REALM}";
  window["env"]["keycloak_client"] = "${KEYCLOAK_CLIENT}";
  window["env"]["refresh_token_validity_seconds"] = "${REFRESH_TOKEN_VALIDITY_SECONDS}";
  window["env"]["community_store_url"] = "${COMMUNITY_STORE_URL}";
})(this);
