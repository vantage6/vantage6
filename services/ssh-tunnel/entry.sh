#!/bin/bash

echo "entrypoint.sh"

# create ssh tunnel using the ssh config created by the node
ssh $@

echo "Done"