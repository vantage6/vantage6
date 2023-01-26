#!/bin/bash

echo "entrypoint.sh"

# set ssh file permissions
chmod 700 /root/.ssh
chmod 600 /root/.ssh/*.pem
chmod 600 /root/.ssh/config
chmod 600 /root/.ssh/known_hosts

if [ -z "$1" ]; then
  echo '' && echo 'Please also provide server name as in config file...' &&
  exit 1
fi

# keep the ssh tunnel alive
while true; do
  ssh -N "$@"
done

echo "Exiting"