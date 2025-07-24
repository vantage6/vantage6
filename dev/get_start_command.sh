#!/bin/bash

# This script checks if the vantage6 server has already been populated with example data.
# If not, it prompts the user to populate the server and runs the necessary devspace pipeline.
# It uses a marker file to track whether the server has been populated.

# Arguments:
#   $1 - Path to the populate marker file

ARGS=("$@")
populate=${ARGS[0]}
POPULATE_MARKER=${ARGS[1]}

# remove the populate marker from the args
ARGS=${ARGS[@]:2}

if [ "$populate" = "true" ]; then
  echo "Running devspace pipeline with populating the server..." >&2
  touch "${POPULATE_MARKER}"
  echo "devspace run-pipeline all-with-populate ${ARGS}"
else
  echo "Running devspace pipeline without populating the server..." >&2
  # Create the marker file to prevent asking the user again
  touch "${POPULATE_MARKER}"
  echo "devspace run-pipeline all-without-populate ${ARGS}"
fi
