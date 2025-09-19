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



# Ensure wsgi picks up the config in dev
export VANTAGE6_CONFIG_LOCATION="${VANTAGE6_STORE_CONFIG_LOCATION}"

# Run with Gunicorn in dev mode (autoreload)
exec gunicorn \
    vantage6.algorithm.store.wsgi:app \
    --bind 0.0.0.0:7602 \
    --worker-class gthread \
    --workers 1 \
    --timeout 120 \
    --graceful-timeout 30 \

echo "exit dev_server.sh"