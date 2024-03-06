#!/bin/sh

# replace environment variables for angular app
envsubst < /usr/share/nginx/html/assets/env.template.js > /usr/share/nginx/html/assets/env.js

# replace environment variables for nginx config. There the URL (without http(s))
# is used in the Content-Security-Policy header.
# TODO the following process to set nginx configuration via sed is not ideal. Consider
# doing it by directly using env vars in nginx.conf (see https://github.com/docker-library/docs/tree/master/nginx#using-environment-variables-in-nginx-configuration-new-in-119)
if [ -z "${SERVER_URL}" ]; then
    SERVER_URL="https://cotopaxi.vantage6.ai"
fi
# Remove http(s) from the server url
SERVER_URL_NO_HTTP=$(echo $SERVER_URL | sed 's/^https\?:\/\///g')
# escape the slashes in the url
SERVER_URL=$(echo $SERVER_URL | sed 's/\//\\\//g')
sed -i "s/<SERVER_URL>/$SERVER_URL/g" /etc/nginx/nginx.conf
sed -i "s/<SERVER_URL_NO_HTTP>/$SERVER_URL_NO_HTTP/g" /etc/nginx/nginx.conf

# also whitelist the allowed algorithm stores in the CSP header
if [ -z "${ALLOWED_ALGORITHM_STORES}" ]; then
    ALLOWED_ALGORITHM_STORES="*"
fi
# escape the slashes in the urls
ALLOWED_ALGORITHM_STORES=$(echo $ALLOWED_ALGORITHM_STORES | sed 's/\//\\\//g')
sed -i "s/<ALGORITHM_STORE_URLS>/$ALLOWED_ALGORITHM_STORES/g" /etc/nginx/nginx.conf
