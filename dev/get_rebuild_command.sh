#!/bin/bash

# Script that takes arguments and returns the appropriate devspace build command
# Usage: ./dev/get_rebuild_command.sh [--server|--node|--store|--ui] [--skip-push]

set -e

DEFAULT_CMD="devspace build"
SELECTED_FLAG=""
SKIP_PUSH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server|--node|--store|--ui)
      SELECTED_FLAG="$1"
      break
      ;;
    --skip-push)
      SKIP_PUSH="--skip-push"
      shift
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

BUILD_CMD="devspace build"
case "$SELECTED_FLAG" in
  --server)
    BUILD_CMD="$BUILD_CMD --profile build-server-only"
    ;;
  --node)
    BUILD_CMD="$BUILD_CMD --profile build-node-only"
    ;;
  --store)
    BUILD_CMD="$BUILD_CMD --profile build-store-only"
    ;;
  --ui)
    BUILD_CMD="$BUILD_CMD --profile build-ui-only"
    ;;
esac

# Add skip-push flag if specified
if [ -n "$SKIP_PUSH" ]; then
    BUILD_CMD="$BUILD_CMD $SKIP_PUSH"
fi

echo "$BUILD_CMD"
