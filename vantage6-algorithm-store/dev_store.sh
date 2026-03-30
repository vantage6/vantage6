#!/bin/sh

echo "*********************************************************************************"
echo "********************* VANTAGE6 STORE DEVELOPMENT MODE ***************************"
echo "*********************************************************************************"

# check if environment variable is set
if [ -z "$VANTAGE6_STORE_CONFIG_LOCATION" ]; then
    echo "VANTAGE6_STORE_CONFIG_LOCATION is not set"
    echo "  using default location /mnt/config.yaml"
    VANTAGE6_STORE_CONFIG_LOCATION="/mnt/config.yaml"
fi


# Run from repo root so module imports don't shadow stdlib modules.
cd /vantage6

python -m vantage6.algorithm.store.init_db "${VANTAGE6_STORE_CONFIG_LOCATION}"
status=$?
if [ "$status" -ne 0 ]; then
    echo "ERROR: failed to initialize algorithm store database" >&2
    exit "$status"
fi

exec uwsgi \
    --py-autoreload 1 \
    --reload-mercy 1 \
    --gevent 100 \
    --http-websockets \
    --http :7602 \
    --master \
    --callable app \
    --disable-logging \
    --wsgi-file /vantage6/vantage6-algorithm-store/vantage6/algorithm/store/wsgi.py \
    --pyargv "${VANTAGE6_STORE_CONFIG_LOCATION}"

echo "exit dev_store.sh"