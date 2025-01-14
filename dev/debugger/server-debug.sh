#!/usr/bin/env bash
# This script is part of vantage6's development environment.
# It starts a vantage6 server in debugging mode using debugpy.
# It expects to find debugpy (pip package) installed on the same directory as
# this script.

set -euo pipefail

log() {
    echo "[$0 | $(date +'%Y-%m-%dT%H:%M:%S%z')]: $*"
}

# This script's directory
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# vantage6 server config path, host, and port
config_file="${VANTAGE6_CONFIG_LOCATION:-/mnt/config.yaml}"
server_host="${VANTAGE6_SERVER_HOST:-0.0.0.0}"
server_port="${VANTAGE6_SERVER_PORT:-80}"
# debugpy: host, port, and path to debugpy package
debugpy_host="${server_host}"
debugpy_port="5678"
debugpy_path="${BASE_DIR}/debugpy"


log "Starting in debugging mode with debugpy.."
if [[ ! -d "${debugpy_path}" ]]; then
    log "Could not find debugpy at ${debugpy_path}!"
    log "If running within a container, was the path set correctly?"
    exit 1
fi

# we need to tell python where to find the debugpy package
export PYTHONPATH="${debugpy_path}"
# 'flask run' uses gevent, we don't use uwsgi here as it's not python code we can pass to debugpy
# TODO: is the above correct?
export GEVENT_SUPPORT=True
log "Flask's development server will be used instead of uWSGI! Will listen on ${server_host}:${server_port} [flask]"
log "Will now be ready for a debugger to attach on ${debugpy_host}:${debugpy_port} [debugpy]!"
# `--wait-for-client` can be passed to debugpy and it will wait for a debugger
# to attach before starting vnode-local
python3 -m debugpy \
    --listen "${debugpy_host}:${debugpy_port}" \
    /usr/local/bin/flask \
        --app "vantage6.server:run_server_app('${config_file}')" \
        run -p "${server_port}" -h "${server_host}"

log "Exiting..."
