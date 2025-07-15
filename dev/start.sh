#!/bin/bash

# This script checks if the vantage6 server has already been populated with example data.
# If not, it prompts the user to populate the server and runs the necessary devspace pipeline.
# It uses a marker file to track whether the server has been populated.

# Arguments:
#   $1 - Path to the populate marker file

POPULATE_MARKER=$1

# Get the profile from environment variable if set
PROFILE_FLAG=""
if [ ! -z "${DEVSPACE_PROFILE}" ]; then
  PROFILE_FLAG="-p ${DEVSPACE_PROFILE}"
fi

# Validate that the POPULATE_MARKER argument is provided
if [ -z "${POPULATE_MARKER}" ]; then
  echo "Error: POPULATE_MARKER argument is required."
  echo "Usage: $0 <POPULATE_MARKER>"
  exit 1
fi

# Check if the marker file exists
if [ ! -f "${POPULATE_MARKER}" ]; then
  echo "Do you want to populate vantage6 server with some example data? (y/n)"
  read -n 1 -s -r answer
  if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
    echo "Populating vantage6 server and starting development environment..."
    touch "${POPULATE_MARKER}"
    devspace run-pipeline all-with-populate ${PROFILE_FLAG}
  else
    echo "Skipping populating vantage6 server."
    # Create the marker file to prevent asking the user again
    touch "${POPULATE_MARKER}"
    devspace run-pipeline all-without-populate ${PROFILE_FLAG}
  fi
else
  # Skip population if the marker file already exists
  echo "Skipping populating vantage6 server. The server is already populated: found marker '${POPULATE_MARKER}'."
  devspace run-pipeline all-without-populate ${PROFILE_FLAG}
fi
