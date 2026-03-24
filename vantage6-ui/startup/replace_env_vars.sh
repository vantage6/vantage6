#!/bin/sh

# replace environment variables for angular app
envsubst < /usr/share/nginx/html/assets/env.template.js > /usr/share/nginx/html/assets/env.js

# replace environment variables for nginx config. There the URL (without http(s))
# is used in the Content-Security-Policy header.
# TODO the following process to set nginx configuration via sed is not ideal. Consider
# doing it by directly using env vars in nginx.conf (see https://github.com/docker-library/docs/tree/master/nginx#using-environment-variables-in-nginx-configuration-new-in-119)
if [ -z "${HQ_URL}" ]; then
    HQ_URL="https://uluru.vantage6.ai"
fi
# Remove http(s) from the HQ url
HQ_URL_NO_HTTP=$(echo "$HQ_URL" | sed 's/^https\?:\/\///g')
# escape the slashes in the url
HQ_URL=$(echo "$HQ_URL" | sed 's/\//\\\//g')
sed -i "s/<HQ_URL>/$HQ_URL/g" /etc/nginx/nginx.conf
sed -i "s/<HQ_URL_NO_HTTP>/$HQ_URL_NO_HTTP/g" /etc/nginx/nginx.conf

# also whitelist the allowed algorithm stores in the CSP header
if [ -z "${ALLOWED_ALGORITHM_STORES}" ]; then
    ALLOWED_ALGORITHM_STORES="*"
fi
# escape the slashes in the urls
ALLOWED_ALGORITHM_STORES=$(echo "$ALLOWED_ALGORITHM_STORES" | sed 's/\//\\\//g')
sed -i "s/<ALGORITHM_STORE_URLS>/$ALLOWED_ALGORITHM_STORES/g" /etc/nginx/nginx.conf

if [ -z "${AUTH_URL}" ]; then
    AUTH_URL="https://auth.uluru.vantage6.ai"
fi
# escape the slashes in the url
AUTH_URL=$(echo "$AUTH_URL" | sed 's/\//\\\//g')
sed -i "s/<AUTH_URL>/$AUTH_URL/g" /etc/nginx/nginx.conf
