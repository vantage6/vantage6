#!/bin/bash

# This script is used to purge data related to the vantage6 development environment.
# It deletes the populate marker file, task directory, server database, and store database.

# Arguments:
#   $1 - Path to the populate marker file
#   $2 - Path to the task directory
#   $3 - Path to the server database mount directory
#   $4 - Path to the store database mount directory

POPULATE_MARKER=$1
TASK_DIRECTORY=$2
SERVER_DATABASE_MOUNT_PATH=$3
STORE_DATABASE_MOUNT_PATH=$4

# Validate that all required arguments are provided
if [ -z "${POPULATE_MARKER}" ] || [ -z "${TASK_DIRECTORY}" ] || [ -z "${SERVER_DATABASE_MOUNT_PATH}" ] || [ -z "${STORE_DATABASE_MOUNT_PATH}" ]; then
  echo "Error: Missing arguments."
  echo "Usage: $0 <POPULATE_MARKER> <TASK_DIRECTORY> <SERVER_DATABASE_MOUNT_PATH> <STORE_DATABASE_MOUNT_PATH>"
  exit 1
fi

echo "Deleting ${POPULATE_MARKER}"
rm -f "${POPULATE_MARKER}"

echo "Deleting all data in ${TASK_DIRECTORY}"
rm -rf "${TASK_DIRECTORY:?}/"*

echo "Deleting all data in ${SERVER_DATABASE_MOUNT_PATH}"
rm -rf "${SERVER_DATABASE_MOUNT_PATH:?}/"*

echo "Deleting all data in ${STORE_DATABASE_MOUNT_PATH}"
rm -rf "${STORE_DATABASE_MOUNT_PATH:?}/"*