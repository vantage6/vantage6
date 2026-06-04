#!/bin/sh

echo "[server.sh start]"

# HTTP listen port (Kubernetes / Docker set V6_PROXY_PORT; default matches image)
HTTP_PORT="${V6_PROXY_PORT:-80}"
# uWSGI async workers (Helm sets 1000 for cluster deployments; local default 100)
GEVENT="${UWSGI_GEVENT:-100}"

# check if environment variable is set
if [ -z "$VANTAGE6_CONFIG_LOCATION" ]; then
    echo "VANTAGE6_CONFIG_LOCATION is not set"
    echo "  using default location /mnt/config.yaml"
    VANTAGE6_CONFIG_LOCATION="/mnt/config.yaml"
fi


# initialize the database
python -m vantage6.hq.init_db "${VANTAGE6_CONFIG_LOCATION}"
status=$?
if [ "$status" -ne 0 ]; then
    echo "ERROR: failed to initialize HQ database" >&2
    exit "$status"
fi

# start HQ
exec uwsgi \
    --http ":${HTTP_PORT}" \
    --gevent "${GEVENT}" \
    --http-websockets \
    --http-chunked-input \
    --http-keepalive \
    --post-buffering 0 \
    --master --callable app --disable-logging \
    --wsgi-file /vantage6/vantage6-hq/vantage6/hq/wsgi.py \
    --pyargv "${VANTAGE6_CONFIG_LOCATION}"

echo "[server.sh exit]"
