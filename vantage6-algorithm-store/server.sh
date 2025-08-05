#!/bin/sh

echo "[server.sh start]"

# check if environment variable is set
if [ -z "$VANTAGE6_CONFIG_LOCATION" ]; then
    echo "VANTAGE6_CONFIG_LOCATION is not set"
    echo "  using default location /mnt/config.yaml"
    VANTAGE6_CONFIG_LOCATION="/mnt/config.yaml"
fi



uwsgi \
    --http :80 \
    --gevent 1000 \
    --http-websockets \
    --master --callable app --disable-logging \
    --wsgi-file \
        /vantage6/vantage6-algorithm-store/vantage6/algorithm/store/wsgi.py \
    --pyargv "${VANTAGE6_CONFIG_LOCATION}"

echo "[server.sh exit]"
