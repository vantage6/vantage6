#!/usr/bin/env bash
# Input environment variables:
#   VANTAGE6_CONFIG_LOCATION: path to the configuration file [default: /mnt/config.yaml]
#   VANTAGE6_SERVER_PORT: port to run the server (if in container, this is the internal port) [default: 80]
#   VANTAGE6_SERVER_HOST: host to run the server on [default: '']
#   VANTAGE6_SERVER_WSGI_FILE: path to wsgi.py [defaut: /vantage6/vantage6-server/vantage6/server/wsgi.py]

set -euo pipefail

# vantage6 server config path, host, and port
config_file="${VANTAGE6_CONFIG_LOCATION:-/mnt/config.yaml}"
server_host="${VANTAGE6_SERVER_HOST:-}"
server_port="${VANTAGE6_SERVER_PORT:-80}"
wsgi_file="${VANTAGE6_SERVER_WSGI_FILE:-/vantage6/vantage6-server/vantage6/server/wsgi.py}"

log() {
    echo "[$0 | $(date +'%Y-%m-%dT%H:%M:%S%z')]: $*"
}


log "Starting..."

if [[ -z "${VANTAGE6_CONFIG_LOCATION:-}" ]]; then
    log "VANTAGE6_CONFIG_LOCATION not set, defaulting to ${config_file}"
fi

log "Starting uWSGI"
uwsgi \
    --http "${server_host}:${server_port}" \
    --gevent 1000 \
    --http-websockets \
    --master --callable app --disable-logging \
    --wsgi-file ${wsgi_file} \
    --pyargv "${config_file}"

log "Exiting..."
