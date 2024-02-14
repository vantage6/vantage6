#!/bin/sh

# replace environment variables for angular app
envsubst < /usr/share/nginx/html/assets/env.template.js > /usr/share/nginx/html/assets/env.js

# replace environment variables for nginx config. There the URL (without http(s))
# is used in the Content-Security-Policy header.
SERVER_URL_NO_HTTP="cotopaxi.vantage6.ai"
if [ ! -z "${SERVER_URL}" ]; then
    SERVER_URL_NO_HTTP=`echo $SERVER_URL | sed 's/^http[s]*:\/\///g'`
fi
sed -i "s/<SERVER_URL>/$SERVER_URL_NO_HTTP/g" /etc/nginx/nginx.conf
# also whitelist the allowed algorithm stores in the CSP header
ALLOWED_ALGORITHM_STORES_NO_HTTP="*"
if [ ! -z "${ALLOWED_ALGORITHM_STORES}" ]; then
    ALLOWED_ALGORITHM_STORES_NO_HTTP=`echo $ALLOWED_ALGORITHM_STORES | sed 's/^http[s]*:\/\///g'`
fi
sed -i "s/<ALGORITHM_STORE_URLS>/$ALLOWED_ALGORITHM_STORES_NO_HTTP/g" /etc/nginx/nginx.conf
