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



uwsgi \
    --py-autoreload 1 \
    --reload-mercy 1 \
    --http :7602 \
    --master \
    --callable app \
    --disable-logging \
    --wsgi-file /vantage6/vantage6-algorithm-store/vantage6/algorithm/store/wsgi.py \
    --pyargv "${VANTAGE6_STORE_CONFIG_LOCATION}"

echo "exit dev_server.sh"