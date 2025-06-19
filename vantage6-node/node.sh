#!/usr/bin/env bash
# Input environment variables:
#   VANTAGE6_CONFIG_LOCATION: path to the configuration file [default: /mnt/config/config.yaml]


set -euo pipefail

config_file="${VANTAGE6_CONFIG_LOCATION:-/mnt/config/config.yaml}"


log() {
    echo "[$(basename $0) | $(date +'%Y-%m-%dT%H:%M:%S%z')]: $*"
}

log "Starting..."

if [[ -z "${VANTAGE6_CONFIG_LOCATION:-}" ]]; then
    log "VANTAGE6_CONFIG_LOCATION not set, defaulting to ${config_file}"
fi

# exec so as to replace the current process with the vnode-local process and it
# can receive signals
exec /usr/local/bin/vnode-local start --dockerized -c "${config_file}"
