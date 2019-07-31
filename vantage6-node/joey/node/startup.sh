#!/bin/sh

pip install -e /src

python /src/joey/node/start.py dl.ai application dev-docker
