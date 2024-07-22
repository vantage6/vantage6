#!/usr/bin/env bash
# Input environment variables:
#   VANTAGE6_CONFIG_LOCATION: path to the configuration file

set -euo pipefail

log() {
    echo "[$(basename $0) | $(date +'%Y-%m-%dT%H:%M:%S%z')]: $*"
}

# vantage6 node config path
config_file="${VANTAGE6_CONFIG_LOCATION:-/mnt/config/config.yaml}"

log "Starting..."

if [[ -z "${VANTAGE6_CONFIG_LOCATION:-}" ]]; then
    log "VANTAGE6_CONFIG_LOCATION not set, defaulting to ${config_file}"
fi

# TODO: Arguments '-n {name}' or "--system"/"--user" were being passed in 'v6
#       node start', were they actully needed?
/usr/local/bin/vnode-local start -c "${config_file}" --dockerized

log "Exiting..."
