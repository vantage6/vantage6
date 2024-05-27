#!/usr/bin/env bash
# Input environment variables:
#   VANTAGE6_CONFIG_LOCATION: path to the configuration file
#   VANTAGE6_SERVER_PORT: port to run the server (if in container, this is the internal port)
#   VANTAGE6_SERVER_HOST: host to run the server on
#   VANTAGE6_DEV_DEBUGPY_PATH: path to debugpy python package
#   VANATGE6_DEV_DEBUGPY_HOST: host to run debugpy on
#   VANTAGE6_DEV_DEBUGPY_PORT: port to run debugpy on

set -euo pipefail

log() {
    echo "[$(basename $0) | $(date +'%Y-%m-%dT%H:%M:%S%z')]: $*"
}

# vantage6 node config path
config_file="${VANTAGE6_CONFIG_LOCATION:-/mnt/config/config.yaml}"
# debugpy: host, port, and path to debugpy package
debugpy_host="${VANTAGE6_DEV_DEBUGPY_HOST:-${server_host}}"
debugpy_port="${VANTAGE6_DEV_DEBUGPY_PORT:-5678}"
debugpy_path="${VANTAGE6_DEV_DEBUGPY_PATH:-}"

log "Starting..."

if [[ -z "${VANTAGE6_CONFIG_LOCATION:-}" ]]; then
    log "VANTAGE6_CONFIG_LOCATION not set, defaulting to ${config_file}"
fi

log "Starting in debugging mode with debugpy.."
if [[ -z "${debugpy_path}" ]]; then
    log "Error: Please set VANTAGE6_DEV_DEBUGPY_PATH to the path where debugpy is installed"
    log "If running within a container, this should be the path where debugpy can be found within it."
    exit 1
elif [[ ! -d "${debugpy_path}" ]]; then
    log "Could not find debugpy at ${debugpy_path}!"
    log "If running within a container, was the path set correctly?"
    exit 1
fi

# we need to tell python where to find the debugpy package
export PYTHONPATH="${debugpy_path}"
log "Will now wait for a debugger to attach on ${debugpy_host}:${debugpy_port} [debugpy]!"
python3 -m debugpy \
    --listen "${debugpy_host}:${debugpy_port}" \
    --wait-for-client \
    /usr/local/bin/vnode-local start -c "${config_file}" --dockerized

log "Exiting..."
