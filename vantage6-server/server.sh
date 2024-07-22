#!/usr/bin/env bash
# Input environment variables:
#   VANTAGE6_CONFIG_LOCATION: path to the configuration file
#   VANTAGE6_SERVER_PORT: port to run the server (if in container, this is the internal port)
#   VANTAGE6_SERVER_HOST: host to run the server on

set -euo pipefail

# vantage6 server config path, host, and port
config_file="${VANTAGE6_CONFIG_LOCATION:-/mnt/config.yaml}"
server_host="${VANTAGE6_SERVER_HOST:-}"
server_port="${VANTAGE6_SERVER_PORT:-80}"

log() {
    echo "[$0 | $(date +'%Y-%m-%dT%H:%M:%S%z')]: $*"
}


log "Starting..."

if [[ -z "${VANTAGE6_CONFIG_LOCATION:-}" ]]; then
    log "VANTAGE6_CONFIG_LOCATION not set, defaulting to ${config_file}"
fi

if [[ -n "${VANTAGE6_DEV_DEBUGPY_HOST:-}" || \
      -n "${VANTAGE6_DEV_DEBUGPY_PORT:-}" || \
      -n "${VANTAGE6_DEV_DEBUGPY_PATH:-}" ]]; then
    log "Warning! A VATAGE6_DEV_DEBUGPY_ environment variable was set, " \
        "however this init script is not meant for debugging purposes."
fi

log "Starting uWSGI"
uwsgi \
    --http "${server_host}:${server_port}" \
    --gevent 1000 \
    --http-websockets \
    --master --callable app --disable-logging \
    --wsgi-file /vantage6/vantage6-server/vantage6/server/wsgi.py \
    --pyargv "${config_file}"

log "Exiting..."
