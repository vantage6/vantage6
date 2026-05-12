#!/bin/sh

echo "[server.sh start]"

# check if environment variable is set
if [ -z "$VANTAGE6_CONFIG_LOCATION" ]; then
    echo "VANTAGE6_CONFIG_LOCATION is not set"
    echo "  using default location /mnt/config.yaml"
    VANTAGE6_CONFIG_LOCATION="/mnt/config.yaml"
fi


# initialize the database
python -m vantage6.algorithm.store.init_db "${VANTAGE6_CONFIG_LOCATION}"
status=$?
if [ "$status" -ne 0 ]; then
    echo "ERROR: failed to initialize algorithm store database" >&2
    exit "$status"
fi

# start the algorithm store
exec uwsgi \
    --http :80 \
    --gevent 100 \
    --http-websockets \
    --master \
    --callable app \
    --disable-logging \
    --wsgi-file /vantage6/vantage6-algorithm-store/vantage6/algorithm/store/wsgi.py \
    --pyargv "${VANTAGE6_CONFIG_LOCATION}"

echo "[server.sh exit]"
