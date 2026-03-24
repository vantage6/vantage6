#!/bin/bash

# This script asks the user if they want to populate the vantage6 hub with some example data.
# If the user says yes, it creates a marker file.

POPULATE_MARKER=$1

# check if the --repopulate flag is provided
explicit_populate=""
for arg in "$@"; do
    if [ "$arg" = "--repopulate" ]; then
        rm -f "${POPULATE_MARKER}"
        echo "Repopulating the vantage6 hub..." >&2
        echo "true"
        exit 0
    elif [ "$arg" = "--populate" ]; then
        explicit_populate="true"
    elif [ "$arg" = "--no-populate" ]; then
        explicit_populate="false"
    fi
done

# Validate that the POPULATE_MARKER argument is provided
if [ -z "${POPULATE_MARKER}" ]; then
  echo "Error: POPULATE_MARKER argument is required." >&2
  echo "Usage: $0 <POPULATE_MARKER>" >&2
  exit 1
fi

if [ ! -f "${POPULATE_MARKER}" ] && [ -n "${explicit_populate}" ]; then
    # populate hasn't been done before, but either --populate or --no-populate was
    # provided, so skip asking the user and set the populate value accordingly.
    echo "Populating hub is set to ${explicit_populate}" >&2
    echo "${explicit_populate}"
elif [ ! -f "${POPULATE_MARKER}" ]; then
    # No populate marker found, so ask the user if they want to populate the hub.
    echo "Do you want to populate vantage6 with test data? (y/n)" >&2
    read -n 1 -s -r answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        echo "Populating vantage6 hub and starting development environment..." >&2
        echo "true"
    else
        echo "false"
    fi
else
    echo "Skipping populating vantage6 hub. The hub is already populated: found marker '${POPULATE_MARKER}'." >&2
    echo "false"
fi