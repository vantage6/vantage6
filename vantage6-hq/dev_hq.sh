#!/bin/sh

echo "*********************************************************************************"
echo "********************** VANTAGE6 HQ DEVELOPMENT MODE *****************************"
echo "*********************************************************************************"

# check if environment variable is set
if [ -z "$VANTAGE6_HQ_CONFIG_LOCATION" ]; then
    echo "VANTAGE6_HQ_CONFIG_LOCATION is not set"
    echo "  using default location /mnt/config.yaml"
    VANTAGE6_HQ_CONFIG_LOCATION="/mnt/config.yaml"
fi

# Run from repo root so module imports don't shadow stdlib modules such as `resource`.
cd /vantage6

# initialize the database
python -m vantage6.hq.init_db "${VANTAGE6_HQ_CONFIG_LOCATION}"

# start HQ
exec uwsgi \
    --py-autoreload 1 \
    --reload-mercy 1 \
    --http :7601 \
    --gevent 100 \
    --http-websockets \
    --master \
    --callable app \
    --disable-logging \
    --module vantage6.hq.wsgi:app \
    --pyargv "${VANTAGE6_HQ_CONFIG_LOCATION}"

echo "exit dev_hq.sh"