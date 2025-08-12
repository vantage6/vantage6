#!/bin/bash

# This script is used to purge data for devspace.
# It deletes the populate marker file, task directory, server database, store database, and keycloak database.

# Arguments:
#   $1 - Path to the populate marker file
#   $2 - Path to the task directory
#   $3 - Path to the server database mount directory
#   $4 - Path to the store database mount directory
#   $5 - Path to the keycloak database mount directory

# Functions
usage() {
  echo "Usage: $0 <POPULATE_MARKER> <TASK_DIRECTORY> <SERVER_DATABASE_MOUNT_PATH> <STORE_DATABASE_MOUNT_PATH>"
  echo "Options:"
  echo "  --help      Display this help message"
  exit 1
}

# Function to replace WSL paths
replace_wsl_path() {
  WSL_REFERENCE_PATH="/run/desktop/mnt/host/wsl"
  WSL_REGULAR_PATH="/mnt/wsl"
  local path=$1
  # If the path contains /run/desktop/mnt/host/wsl, replace it with /mnt/wsl
  if [[ "$path" == $WSL_REFERENCE_PATH* ]]; then
    path="${WSL_REGULAR_PATH}${path#${WSL_REFERENCE_PATH}}"
  fi
  echo "$path"
}

if [[ "$1" == "--help" ]]; then
  usage
fi

POPULATE_MARKER=$(replace_wsl_path "$1")
TASK_DIRECTORY=$(replace_wsl_path "$2")
SERVER_DATABASE_MOUNT_PATH=$(replace_wsl_path "$3")
STORE_DATABASE_MOUNT_PATH=$(replace_wsl_path "$4")

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
  fi
done

echo "Deleting ${POPULATE_MARKER}"
rm -f "$POPULATE_MARKER" || { echo "Failed to delete $POPULATE_MARKER"; }

delete_all_in_dir() {
  local dir="$1"
  echo "Deleting all data in ${dir}"

  need_sudo=0
  # Function to check write permissions recursively
  check_permissions() {
    local path="$1"
    for item in "$path"/*; do
      if [ -e "$item" ]; then
        if [ ! -w "$item" ]; then
          need_sudo=1
          return
        fi
        # If it's a directory, check its contents recursively
        if [ -d "$item" ]; then
          check_permissions "$item"
          # If we found a permission issue, stop checking
          if [ $need_sudo -eq 1 ]; then
            return
          fi
        fi
      fi
    done
  }

  check_permissions "$dir"

  # Check if directory is writable by current user
  if [ $need_sudo -eq 0 ]; then
    rm -rf "${dir}/"* || { echo "Failed to delete data in $dir"; }
  else
    echo "Directory $dir is not writable, attempting to use sudo to empty it..."
    sudo rm -rf "${dir}/"* || { echo "Failed to delete data in $dir (even with sudo)"; }
  fi
}

delete_all_in_dir "$TASK_DIRECTORY"
delete_all_in_dir "$SERVER_DATABASE_MOUNT_PATH"
delete_all_in_dir "$STORE_DATABASE_MOUNT_PATH"

echo "Purge completed successfully."