#!/bin/sh

pip install -e /src

python /src/vantage/node/start.py $1 $2 dev-docker
