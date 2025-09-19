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

# Ensure wsgi picks up the config in dev
export VANTAGE6_CONFIG_LOCATION="${VANTAGE6_SERVER_CONFIG_LOCATION}"

# Run with Gunicorn in dev mode (autoreload)
exec gunicorn \
    vantage6.server.wsgi:app \
    --bind 0.0.0.0:7601 \
    --worker-class gevent \
    --workers 1 \
    --timeout 120 \
    --graceful-timeout 30 \
    --reload \
    --reload-engine poll

echo "exit dev_server.sh"