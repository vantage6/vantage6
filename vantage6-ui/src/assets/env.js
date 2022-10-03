// The purpose of this file is to be able to insert environment variables from Docker
(function(window) {
    window["env"] = window["env"] || {};

    // Environment variables
    window["env"]["api_url"] = "https://petronas.vantage6.ai";
})(this);