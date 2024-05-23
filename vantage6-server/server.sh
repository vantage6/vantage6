#!/usr/bin/env bash
# Input environment variables:
#   VANTAGE6_CONFIG_LOCATION: path to the configuration file
#   VANTAGE6_SERVER_PORT: port to run the server (if in container, this is the internal port)
#   VANTAGE6_SERVER_HOST: host to run the server on
#   VANTAGE6_DEV_DEBUGPY_RUN: whether to run debugpy or not
#   VANTAGE6_DEV_DEBUGPY_PATH: path to debugpy python package
#   VANATGE6_DEV_DEBUGPY_HOST: host to run debugpy on
#   VANTAGE6_DEV_DEBUGPY_PORT: port to run debugpy on
# TODO: Split this script into two separate scripts, one for "production" and one for debug

set -euo pipefail

log() {
    echo "[server.sh | $(date +'%Y-%m-%dT%H:%M:%S%z')]: $*"
}

# vantage6 server config path, host, and port
config_file="${VANTAGE6_CONFIG_LOCATION:-/mnt/config.yaml}"
server_host="${VANTAGE6_SERVER_HOST:-0.0.0.0}"
server_port="${VANTAGE6_SERVER_PORT:-80}"
# debugpy: whether to run debugpy or not
debugpy_run="${VANTAGE6_DEV_DEBUGPY_RUN:-False}"
# debugpy: host, port, and path to debugpy package
debugpy_host="${VANTAGE6_DEV_DEBUGPY_HOST:-${server_host}}"
debugpy_port="${VANTAGE6_DEV_DEBUGPY_PORT:-5678}"
debugpy_path="${VANTAGE6_DEV_DEBUGPY_PATH:-}"

log "Starting..."

if [ -z "${VANTAGE6_CONFIG_LOCATION:-}" ]; then
    log "VANTAGE6_CONFIG_LOCATION not set, defaulting to ${config_file}"
fi

if [ "${debugpy_run}" == "True" ]; then
    log "Starting in debugging mode with debugpy.."
    if [ -z "${debugpy_path}" ]; then
        log "VANTAGE6_DEV_DEBUGPY_RUN is set to True, but VANTAGE6_DEV_DEBUGPY_PATH is not set!"
        log "Please set VANTAGE6_DEV_DEBUGPY_PATH to the path where debugpy is installed (within the container)"
        exit 1
    fi
    if [ ! -d "${debugpy_path}" ]; then
        log "Could not find debugpy at ${debugpy_path}!"
        log "It must be mounted in the container at the specified path!"
        exit 1
    fi
    export PYTHONPATH="${debugpy_path}"
    export GEVENT_SUPPORT=True
    log "Flask's development server will used instead of uWSGI!"
    log "Will now wait for a debugger to attach on ${debugpy_host}:${debugpy_port} [debugpy]!"
    python3 -m debugpy \
        --listen "${debugpy_host}:${debugpy_port}" \
        --wait-for-client \
        /usr/local/bin/flask \
            --app "vantage6.server:run_dev_debug_server('${config_file}')" \
            run -p "${server_port}" -h "${server_host}"
else
    log "Starting uWSGI"
    # TODO: confirm '--http :port' = '--http 0.0.0.0:port'
    uwsgi \
        --http "${VANTAGE6_SERVER_HOST:-}:${server_port}" \
        --gevent 1000 \
        --http-websockets \
        --master --callable app --disable-logging \
        --wsgi-file /vantage6/vantage6-server/vantage6/server/wsgi.py \
        --pyargv "${config_file}"
fi

log "Exiting..."
