# `make` is expected to be called from the directory that contains
# this Makefile

TAG ?= petronas
REGISTRY ?= harbor2.vantage6.ai

help:
	@echo "Available commands to 'make':"
	@echo "  set-version          : set version (e.g set-version FLAGS=\"--version 2.0.0 --build 0 --spec alpha\")"
	@echo "  uninstall            : uninstall all vantage6 packages"
	@echo "  install              : do a regular install of all vantage6 packages"
	@echo "  install-dev          : do an editable install of all vantage6 packages"
	@echo "  image                : build the node/server docker image"
	@echo "  base-image           : build the infrastructure base image"
	@echo "  algorithm-base-image : build the algorithm base image"
	@echo "  support-image        : build the supporing images"
	@echo "  rebuild              : rebuild all python packages"
	@echo "  publish              : publish built python packages to pypi.org (BE CAREFUL!)"
	@echo "  community            : notify community FLAGS="--version 99.99.88 --notes 'I should have done more!' --post-notes 'Oh.. Maybe not'""
	@echo "  test                 : run all unittests and compute coverage"
	@echo ""
	@echo "Using "
	@echo "  tag:      ${TAG}"
	@echo "  registry: ${REGISTRY}"

set-version:
	# --version --build --spec --post
	cd tools && ls
	cd tools && python update-version.py ${FLAGS}

community:
	#  make community FLAGS="--version 99.99.88 --notes 'I should have done more!' --post-notes 'Oh.. Maybe not'"
	cd tools && python update-discord.py ${FLAGS}

uninstall:
	pip uninstall -y vantage6
	pip uninstall -y vantage6-client
	pip uninstall -y vantage6-common
	pip uninstall -y vantage6-node
	pip uninstall -y vantage6-server

install:
	cd vantage6-common && pip install .
	cd vantage6-client && pip install .
	cd vantage6 && pip install .
	cd vantage6-node && pip install .
	cd vantage6-server && pip install .

install-dev:
	cd vantage6-common && pip install -e .
	cd vantage6-client && pip install -e .
	cd vantage6 && pip install -e .
	cd vantage6-node && pip install -e .
	cd vantage6-server && pip install -e .

base-image:
	@echo "Building ${REGISTRY}/infrastructure/infrastructure-base:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/infrastructure-base:${TAG} \
		--platform linux/arm64,linux/amd64 \
		-f ./docker/infrastructure-base.Dockerfile \
		--push .

algorithm-base-image:
	@echo "Building ${REGISTRY}/algorithms/algorithm-base:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/algorithm-base:${TAG} \
		--platform linux/arm64,linux/amd64 \
		-f ./docker/algorithm-base.Dockerfile \
		--push .

support-image:
	@echo "Building ${REGISTRY}/infrastructure/alpine:${TAG}"
	@echo "Building ${REGISTRY}/infrastructure/vpn-client:${TAG}"
	@echo "Building ${REGISTRY}/infrastructure/vpn-configurator:${TAG}"
	@echo "All images are also tagged with `latest`"

	docker buildx build \
		--tag ${REGISTRY}/infrastructure/alpine:${TAG} \
		--tag ${REGISTRY}/infrastructure/alpine:latest \
		--platform linux/arm64,linux/amd64 \
		-f ./docker/alpine.Dockerfile \
		--push .

	docker buildx build \
		--tag ${REGISTRY}/infrastructure/vpn-client:${TAG} \
		--tag ${REGISTRY}/infrastructure/vpn-client:latest \
		--platform linux/arm64,linux/amd64 \
		-f ./docker/vpn-client.Dockerfile \
		--push .

	docker buildx build \
		--tag ${REGISTRY}/infrastructure/vpn-configurator:${TAG} \
		--tag ${REGISTRY}/infrastructure/vpn-configurator:latest \
		--platform linux/arm64,linux/amd64 \
		-f ./docker/vpn-configurator.Dockerfile \
		--push .

image:
	@echo "Building ${REGISTRY}/infrastructure/node:${TAG}"
	@echo "Building ${REGISTRY}/infrastructure/server:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/node:${TAG} \
		--tag ${REGISTRY}/infrastructure/server:${TAG} \
		--platform linux/arm64,linux/amd64 \
		-f ./docker/node-and-server.Dockerfile \
		--push .

rebuild:
	@echo "------------------------------------"
	@echo "         BUILDING PROJECT           "
	@echo "------------------------------------"
	@echo "------------------------------------"
	@echo "         VANTAGE6 COMMON            "
	@echo "------------------------------------"
	cd vantage6-common && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 CLIENT            "
	@echo "------------------------------------"
	cd vantage6-client && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 CLI            "
	@echo "------------------------------------"
	cd vantage6 && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 NODE            "
	@echo "------------------------------------"
	cd vantage6-node && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 SERVER            "
	@echo "------------------------------------"
	cd vantage6-server && make rebuild

publish:
	cd vantage6-common && make publish
	cd vantage6-client && make publish
	cd vantage6 && make publish
	cd vantage6-node && make publish
	cd vantage6-server && make publish

test:
	coverage run --source=vantage6 --omit="utest.py","*.html","*.htm","*.txt","*.yml","*.yaml" utest.py
