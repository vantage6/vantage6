#!/bin/bash
set -e

apt-get update && apt-get install -y netcat-openbsd

uwsgi --http :7601 \
  --gevent 1000 \
  --http-websockets \
  --http-chunked-input \
  --http-keepalive \
  --post-buffering 0 \
  --master \
  --callable app \
  --disable-logging \
  --wsgi-file /vantage6/vantage6-server/vantage6/server/wsgi.py \
  --pyargv /mnt/config.yaml &
SERVER_PID=$!

while ! nc -z localhost 7601; do
  sleep 1
done

vserver-local import -c /mnt/config.yaml /mnt/import.yaml

wait $SERVER_PID
