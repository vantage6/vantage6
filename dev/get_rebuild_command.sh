#!/bin/bash

# Script that takes arguments and returns the appropriate devspace build command
# Usage: ./dev/get_rebuild_command.sh [--hq|--node|--store|--ui]

set -e

DEFAULT_CMD="devspace build"
SELECTED_FLAG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hq|--node|--store|--ui)
      SELECTED_FLAG="$1"
      break
      ;;
    --)
      shift
      break
      ;;
    *)
      shift
      ;;
  esac

done

case "$SELECTED_FLAG" in
  --hq)
    echo "devspace build --profile build-hq-only"
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
    echo "$DEFAULT_CMD"
    ;;
esac