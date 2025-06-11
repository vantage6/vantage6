// The purpose of this file is to be able to insert environment variables from Docker
(function(window) {
    window["env"] = window["env"] || {};

    // Environment variables
    window["env"]["server_url"] = "https://cotopaxi.vantage6.ai";
    window["env"]["api_path"] = "";
    window["env"]["allowed_algorithm_stores"] = "*";
    window["env"]["community_store_url"] = "https://store.cotopaxi.vantage6.ai/api";
})(this);