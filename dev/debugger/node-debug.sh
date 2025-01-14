#!/usr/bin/env bash
# This script is part of vantage6's development environment.
# It starts a vantage6 node in debugging mode using debugpy.
# It expects to find debugpy (pip package) installed on the same directory as
# this script.

set -euo pipefail

log() {
    echo "[$(basename $0) | $(date +'%Y-%m-%dT%H:%M:%S%z')]: $*"
}

# This script's directory
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# vantage6 node config path
config_file="${VANTAGE6_CONFIG_LOCATION:-/mnt/config/config.yaml}"

# debugpy: host, port, and path to debugpy package
debugpy_host="0.0.0.0"
debugpy_port="5678"
debugpy_path="${BASE_DIR}/debugpy"

log "Starting..."

log "Starting in debugging mode with debugpy.."
if [[ ! -d "${debugpy_path}" ]]; then
    log "Could not find debugpy at ${debugpy_path}!"
    log "If running within a container, was the path set correctly?"
    exit 1
fi

# we need to tell python where to find the debugpy package
export PYTHONPATH="${debugpy_path}"
log "Will now wait for a debugger to attach on ${debugpy_host}:${debugpy_port} [debugpy]!"
# `--wait-for-client` can be passed to debugpy and it will wait for a debugger
# to attach before starting vnode-local
python3 -m debugpy \
    --wait-for-client \
    --listen "${debugpy_host}:${debugpy_port}" \
    /usr/local/bin/vnode-local start -c "${config_file}" --dockerized

log "Exiting..."
