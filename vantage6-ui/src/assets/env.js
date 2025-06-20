// The purpose of this file is to be able to insert environment variables from Docker
(function(window) {
    window["env"] = window["env"] || {};

    // Environment variables
    window["env"]["server_url"] = "https://cotopaxi.vantage6.ai";
    window["env"]["api_path"] = "";
    window["env"]["api_url"] = "https://cotopaxi.vantage6.ai";
    window["env"]["allowed_algorithm_stores"] = "*";
    window["env"]["auth_url"] = "https://auth.cotopaxi.vantage6.ai";
    window["env"]["keycloak_realm"] = "vantage6";
    window["env"]["keycloak_client"] = "myclient";
})(this);