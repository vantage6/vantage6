#!/bin/bash

# start a node for each config file the provided directory

config_dir=$1
if [ -z "$config_dir" ]; then
    echo "Provide a configuration directory as argument"
    exit 1
fi

for config in $config_dir/*.yaml; do
    echo "Starting node with config: $config"
    python /vantage6/vantage6-node/vantage6/dev_start.py "$config" &
done

# For development purposes, we put infinite sleep here. This has the advantage that
# once the node crashes, the container will keep running and therefore, the error will
# remain visible in the logs. A restart of the container would obfuscate the error
# which should not happen in development.
sleep infinity
