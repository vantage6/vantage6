#!/bin/bash

# get path where this script is
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR=$(realpath $DIR/../..)
NODE=$1

# node must be one of 'mars', 'jupiter', 'saturn':
if [ "$NODE" != "mars" ] && [ "$NODE" != "jupiter" ] && [ "$NODE" != "saturn" ]; then
    echo "Usage: $0 <node>"
    echo "  node must be one of 'mars', 'jupiter', 'saturn'"
    exit 1
fi

# we use relative paths (to repo root) in node config file
cd ${REPO_DIR}

source "${REPO_DIR}/dev/venv/bin/activate"

v6 node start --mount-src ${REPO_DIR} --config $(realpath ${REPO_DIR}/dev/nodes/${NODE}/config.yaml) --attach
