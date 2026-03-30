#!/bin/bash

# This script deletes Keycloak's PersistentVolumeClaims and associated PersistentVolumes
# It is used as part of the devspace purge process to ensure clean removal of Keycloak's storage

echo "Deleting keycloak's PVCs..."
kubectl get pvc -l app.kubernetes.io/instance=vantage6-auth -o name | xargs -r kubectl delete

echo "Deleting keycloak's PersistentVolumes..."
# Get all PVs that were bound to the deleted PVCs
PV_NAMES=$(kubectl get pvc -l app.kubernetes.io/instance=vantage6-auth -o jsonpath='{.items[*].spec.volumeName}')
if [ ! -z "$PV_NAMES" ]; then
  for pv in $PV_NAMES; do
    kubectl delete pv "$pv"
  done
fi


echo "Keycloak storage cleanup completed."