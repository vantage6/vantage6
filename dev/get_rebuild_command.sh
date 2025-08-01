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

# Use case statement to handle different image types
case "$1" in
    --server)
        echo "devspace build --profile build-server-only"
        ;;
    --node)
        echo "devspace build --profile build-node-only"
        ;;
    --store)
        echo "devspace build --profile build-store-only"
        ;;
    --ui)
        echo "devspace build --profile build-ui-only"
        ;;
    *)
        echo "Invalid argument: $1" >&2
        echo "Valid arguments are: --server, --node, --store, --ui" >&2
        exit 1
        ;;
esac