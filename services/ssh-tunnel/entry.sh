#!/bin/bash

echo "entrypoint.sh"

# ls /root


ssh -fN $@

echo "sleeping"
sleep infinity

echo "Done"