#!/bin/bash

# get path where this script is
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR=$(realpath $DIR/../..)

source $REPO_DIR/dev/venv/bin/activate

v6 server start --mount-src ${REPO_DIR} --config $(realpath ${REPO_DIR}/dev/servers/planets/config.yaml) --with-ui --ui-port 8060 --attach

