#!/bin/bash

# This script asks the user if they want to populate the vantage6 server with some example data.
# If the user says yes, it creates a marker file.

POPULATE_MARKER=$1

# check if the --repopulate flag is provided
for arg in "$@"; do
    if [ "$arg" = "--repopulate" ]; then
        rm -f "${POPULATE_MARKER}"
        echo "Repopulating the server..." >&2
        echo "true"
        exit 0
    fi
done

# Validate that the POPULATE_MARKER argument is provided
if [ -z "${POPULATE_MARKER}" ]; then
  echo "Error: POPULATE_MARKER argument is required." >&2
  echo "Usage: $0 <POPULATE_MARKER>" >&2
  exit 1
fi

if [ ! -f "${POPULATE_MARKER}" ]; then
    echo "Do you want to populate vantage6 server with some example data? (y/n)" >&2
    read -n 1 -s -r answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        echo "Populating vantage6 server and starting development environment..." >&2
        echo "true"
    else
        echo "false"
    fi
else
    echo "Skipping populating vantage6 server. The server is already populated: found marker '${POPULATE_MARKER}'." >&2
    echo "false"
fi