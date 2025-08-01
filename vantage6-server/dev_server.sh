#!/bin/sh

echo "*********************************************************************************"
echo "******************** VANTAGE6 SERVER DEVELOPMENT MODE ***************************"
echo "*********************************************************************************"

# check if environment variable is set
if [ -z "$VANTAGE6_SERVER_CONFIG_LOCATION" ]; then
    echo "VANTAGE6_SERVER_CONFIG_LOCATION is not set"
    echo "  using default location /mnt/config.yaml"
    VANTAGE6_SERVER_CONFIG_LOCATION="/mnt/config.yaml"
fi



uwsgi \
    --py-autoreload 1 \
    --reload-mercy 1 \
    --http :7601 \
    --gevent 1000 \
    --http-websockets \
    --master \
    --callable app \
    --disable-logging \
    --wsgi-file /vantage6/vantage6-server/vantage6/server/wsgi.py \
    --pyargv "${VANTAGE6_SERVER_CONFIG_LOCATION}"

echo "exit dev_server.sh"