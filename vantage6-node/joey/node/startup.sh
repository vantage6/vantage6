#!/bin/sh

pip install -e /src

python /src/joey/node/start.py $1 $2 dev-docker
