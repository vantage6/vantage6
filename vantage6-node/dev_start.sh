#!/bin/bash

# start a node for each config file the provided directory

config_dir=$1
if [ -z "$config_dir" ]; then
    echo "Provide a configuration directory as argument"
    exit 1
fi

# Remove trailing slashes from config_dir
config_dir=${config_dir%/}

for dir in $config_dir/*; do
    if [ -d "$dir" ]; then
        echo "Looking for node configurations in: $dir"

        config=$(find "$dir" -maxdepth 1 -name "*.yaml" -type f)
        dotenv_file="$dir"/.env

        # Check if the config file exists
        if [ ! -f "$config" ]; then
            echo "No yaml config file found in $dir/*.yaml"
            continue
        fi

        # Check if the .env file exists
        if [ ! -f "$dotenv_file" ]; then
            echo "No .env file found in $dir/.env"
            continue
        fi

        # Source the .env file to set environment variables in their own shell as we
        # start a new shell for each node
        bash -c "source \"$dotenv_file\" && python /vantage6/vantage6-node/vantage6/dev_start.py \"$config\" &"
    fi
done

# For development purposes, we put infinite sleep here. This has the advantage that
# once the node crashes, the container will keep running and therefore, the error will
# remain visible in the logs. A restart of the container would obfuscate the error
# which should not happen in development.
sleep infinity
