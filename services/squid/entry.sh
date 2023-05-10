#!/bin/bash

echo "entrypoint.sh"

# start the squid service
echo "Starting squid..."
tail -F /var/log/squid/access.log 2>/dev/null &
tail -F /var/log/squid/error.log 2>/dev/null &
tail -F /var/log/squid/store.log 2>/dev/null &
tail -F /var/log/squid/cache.log 2>/dev/null &

squid -N -f /etc/squid/squid.conf

echo "Exiting"