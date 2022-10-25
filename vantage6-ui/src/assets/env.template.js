// The purpose of this file is to be able to insert environment variables from Docker
(function(window) {
    window["env"] = window["env"] || {};

    // Environment variables
    window["env"]["api_url"] = "${API_URL}";
    window["env"]["server_url"] = "${SERVER_URL}";
    window["env"]["api_path"] = "${API_PATH}";
})(this);