#!/usr/bin/env bash
# Proof-of-concept!

set -euo pipefail

# Path to top of project directory
TOP_DIR=$(git rev-parse --show-toplevel)
# Path to python virtual environment
VENV_PATH="$TOP_DIR/dev/venv"
# Image used to install debugpy | TODO: meant for multi-arch, does it work?
V6_IMAGE_DEBUGPY="harbor2.vantage6.ai/infrastructure/infrastructure-base"
# Path where debugpy will be installed locally, later to be mounted in containers
DEBUGPY_DIR="$TOP_DIR/dev/debugpy"

cd $TOP_DIR

echo "Creating python virtual environment"
python3 -m venv $VENV_PATH

echo "Activating python virtual environment"
source $VENV_PATH/bin/activate

echo "Installing vantage6 packages"
make install-dev

echo "Installing debugpy for later use within containers via volume mount"
pip install debugpy --target "${DEBUGPY_DIR}"
# TODO: Something like the below might be needed if host arch is different from container arch?
# docker run --user $(id -u):$(id -g) \
#            -v "$DEBUGPY_DIR:/tmp/debugpy" \
#            $V6_IMAGE_DEBUGPY \
#            pip install debugpy --target /tmp/debugpy
