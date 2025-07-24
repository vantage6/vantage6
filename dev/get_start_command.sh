#!/bin/bash

# This script checks if the vantage6 server has already been populated with example data.
# If not, it prompts the user to populate the server and runs the necessary devspace pipeline.
# It uses a marker file to track whether the server has been populated.

# Arguments:
#   $1 - Path to the populate marker file

ARGS=("$@")
populate=${ARGS[0]}
POPULATE_MARKER=${ARGS[1]}

# remove the populate args from the args so that the rest can be passed to devspace
ARGS=${ARGS[@]:2}

# remove the --repopulate flag from the args as that should not be passed to devspace
filtered_args=()
for arg in $ARGS; do
  if [ "$arg" != "--repopulate" ]; then
    filtered_args+=" $arg"
  fi
done
ARGS=$filtered_args

if [ "$populate" = "true" ]; then
  echo "Running devspace pipeline with populating the server..." >&2
  # Note that we don't create the marker file here because it is created by the
  # devspace pipeline when the populate script has successfully run.
  echo "devspace run-pipeline all-with-populate ${ARGS}"
else
  echo "Running devspace pipeline without populating the server..." >&2
  # Create the marker file to prevent asking the user again
  touch "${POPULATE_MARKER}"
  echo "devspace run-pipeline all-without-populate ${ARGS}"
fi
