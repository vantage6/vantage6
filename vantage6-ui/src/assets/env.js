// The purpose of this file is to be able to insert environment variables from Docker
(function(window) {
    window["env"] = window["env"] || {};

    // Environment variables
    window["env"]["server_url"] = "https://petronas.vantage6.ai";
    window["env"]["api_path"] = "";
    window["env"]["api_url"] = "https://petronas.vantage6.ai";
})(this);