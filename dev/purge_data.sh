#!/bin/bash

# This script is used to purge data for devspace.
# It deletes the populate marker file, task directory, server database, and store database.

# Arguments:
#   $1 - Path to the populate marker file
#   $2 - Path to the task directory
#   $3 - Path to the server database mount directory
#   $4 - Path to the store database mount directory

# Functions
usage() {
  echo "Usage: $0 <POPULATE_MARKER> <TASK_DIRECTORY> <SERVER_DATABASE_MOUNT_PATH> <STORE_DATABASE_MOUNT_PATH>"
  echo "Options:"
  echo "  --help      Display this help message"
  exit 1
}

if [[ "$1" == "--help" ]]; then
  usage
fi

POPULATE_MARKER=$1
TASK_DIRECTORY=$2
SERVER_DATABASE_MOUNT_PATH=$3
STORE_DATABASE_MOUNT_PATH=$4

# Validate that all required arguments are provided
if [ -z "${POPULATE_MARKER}" ] || [ -z "${TASK_DIRECTORY}" ] || [ -z "${SERVER_DATABASE_MOUNT_PATH}" ] || [ -z "${STORE_DATABASE_MOUNT_PATH}" ]; then
  echo "Error: Missing arguments."
  usage
fi

# Validate the paths
for path in "$POPULATE_MARKER" "$TASK_DIRECTORY" "$SERVER_DATABASE_MOUNT_PATH" "$STORE_DATABASE_MOUNT_PATH"; do
  # validate that the path is not empty or root
  if [[ "$path" == "/" || -z "$path" ]]; then
    echo "Error: Invalid path provided: $path"
    exit 1
  fi
  # validate that the path exists
  if [[ ! -e "$path" ]]; then
    echo "Error: Path does not exist: $path"
    exit 1
  fi
done

echo "Deleting ${POPULATE_MARKER}"
rm -f "$POPULATE_MARKER" || { echo "Failed to delete $POPULATE_MARKER"; }

echo "Deleting all data in ${TASK_DIRECTORY}"
rm -rf "${TASK_DIRECTORY}/"* || { echo "Failed to delete data in $TASK_DIRECTORY"; }

echo "Deleting all data in ${SERVER_DATABASE_MOUNT_PATH}"
rm -rf "${SERVER_DATABASE_MOUNT_PATH}/"* || { echo "Failed to delete data in $SERVER_DATABASE_MOUNT_PATH"; }

echo "Deleting all data in ${STORE_DATABASE_MOUNT_PATH}"
rm -rf "${STORE_DATABASE_MOUNT_PATH}/"* || { echo "Failed to delete data in $STORE_DATABASE_MOUNT_PATH"; }

echo "Purge completed successfully."