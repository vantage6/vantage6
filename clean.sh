# Clean up local Docker images
devspace cleanup images

# Clean up local registry
devspace cleanup local-registry

# Reset dev container
devspace reset pods

# Remove deployments from cluster
devspace purge

# Reset cached variables
devspace reset vars
