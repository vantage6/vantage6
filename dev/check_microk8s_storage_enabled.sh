#!/bin/bash

# This script checks if the developer has microk8s installed. If so, it must have
# hostpath-storage enabled for the devspace to work. This is checked, and will exit with 
# an error if it is not enabled.

if command -v microk8s >/dev/null 2>&1; then
  current_context=$(microk8s kubectl config current-context 2>/dev/null)
  if [[ "$current_context" == "microk8s" ]]; then
    storage_enabled=$(microk8s status | awk '/enabled:/, /disabled:/' | grep -q 'hostpath-storage' && echo true || echo false)
    if [ "$storage_enabled" = "false" ]; then
      echo "--------------------------------"
      echo "ERROR: Storage is not enabled! The authentication service will not work"
      echo "ERROR: Run 'microk8s enable hostpath-storage' to fix this"
      echo "--------------------------------"
      exit 1
    fi
  fi
fi