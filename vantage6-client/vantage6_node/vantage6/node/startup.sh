#!/bin/sh

pip install -e /src

python /src/vantage6/node/start.py $1 $2 dev-docker
