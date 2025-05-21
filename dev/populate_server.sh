#!/bin/bash

# This script checks if the vantage6 server has already been populated with example data.
# If not, it prompts the user to populate the server and runs the necessary devspace pipeline.
# It uses a marker file to track whether the server has been populated.

# Arguments:
#   $1 - Path to the populate marker file

POPULATE_MARKER=$1

# Validate that the POPULATE_MARKER argument is provided
if [ -z "${POPULATE_MARKER}" ]; then
  echo "Error: POPULATE_MARKER argument is required."
  echo "Usage: $0 <POPULATE_MARKER>"
  exit 1
fi

# Check if the marker file exists
if [ ! -f "${POPULATE_MARKER}" ]; then
  echo "Do you want to populate vantage6 server with some example data? (y/n)"
  read -r answer
  if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
    # Run the pipeline to populate the server
    echo "Starting to populate vantage6 server..."
    devspace run-pipeline init
    INIT_STATUS=$?
    if [ $INIT_STATUS -eq 0 ]; then
      echo "Populating vantage6 server completed successfully."
      # Create the marker file to indicate the server has been populated
      mkdir -p .devspace
      touch "${POPULATE_MARKER}"
    else
      echo "Error: Failed to populate vantage6 server. The init pipeline did not complete successfully (exit code: $INIT_STATUS)."
      exit $INIT_STATUS
    fi
  else
    echo "Skipping populating vantage6 server."
  fi
else
  # Skip population if the marker file already exists
  echo "Skipping populating vantage6 server. The server is already populated: found marker '${POPULATE_MARKER}'."
fi
