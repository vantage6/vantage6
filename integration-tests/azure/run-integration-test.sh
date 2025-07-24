#!/bin/bash
docker compose -f docker-compose-azure-dev.yml  up -d --build
docker build ../.. --no-cache -f ../../docker/algorithm-base.Dockerfile -t large-data-test-algorithm-base:latest
docker build ./dhd-test-algorithm/ --no-cache -t localhost:5000/dhd-test-algorithm:latest
docker push localhost:5000/dhd-test-algorithm:latest
docker build ../.. --no-cache -f ../../docker/infrastructure-base.Dockerfile -t harbor2.vantage6.ai/infrastructure/infrastructure-base:TEST
docker build ../.. --no-cache -f ../../docker/node-and-server.Dockerfile --build-arg BASE=TEST -t test-node:latest
vnode stop --name alpha
vnode stop --name beta
vnode stop --name gamma
vnode start --name alpha --image test-node:latest
vnode start --name beta --image test-node:latest
vnode start --name gamma --image test-node:latest
docker logs vantage6-alpha-user -f