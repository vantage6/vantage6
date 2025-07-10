#!/bin/bash

# Script that takes arguments and returns the appropriate devspace build command
# Usage: ./dev/get_rebuild_command.sh [--server|--node|--store|--ui]

set -e

# if no args are provided, build all images
if [ $# -eq 0 ]; then
    echo "devspace build"
    exit 0
elif [ $# -gt 1 ]; then
    echo "Please provide only one argument." >&2
    echo "Usage: $0 [--server|--node|--store|--ui]" >&2
    exit 1
fi

# check if arg is equal to server, node, store, or ui
image_to_build=$1
if [[ "$image_to_build" == "--server" || "$image_to_build" == "--node" || "$image_to_build" == "--store" || "$image_to_build" == "--ui" ]]; then
    # remove the -- from the arg
    image_name=$(echo "$image_to_build" | sed 's/^--//')
    echo "devspace build --profile build-$image_name-only"
    exit 0
else
    echo "Invalid argument: $image_to_build" >&2
    echo "Valid arguments are: --server, --node, --store, --ui" >&2
    exit 1
fi