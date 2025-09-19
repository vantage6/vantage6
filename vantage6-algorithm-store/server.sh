#!/bin/sh

echo "[server.sh start]"

# check if environment variable is set
if [ -z "$VANTAGE6_CONFIG_LOCATION" ]; then
    echo "VANTAGE6_CONFIG_LOCATION is not set"
    echo "  using default location /mnt/config.yaml"
    VANTAGE6_CONFIG_LOCATION="/mnt/config.yaml"
fi



# Run with Gunicorn (wsgi reads config path from VANTAGE6_CONFIG_LOCATION)
exec gunicorn \
    vantage6.algorithm.store.wsgi:app \
    --bind 0.0.0.0:80 \
    --worker-class gthread \
    --workers 2 \
    --timeout 120 \
    --graceful-timeout 30

echo "[server.sh exit]"
