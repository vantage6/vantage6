# `make` is expected to be called from the directory that contains
# this Makefile

# docker image tag
TAG ?= cotopaxi
REGISTRY ?= harbor2.vantage6.ai
PLATFORMS ?= linux/arm64,linux/amd64
# Example for local development
# TAG ?= local
# REGISTRY ?= localhost
# PLATFORMS ?= linux/amd64

# infrastructure base image version
BASE ?= 4.0

# Use `make PUSH_REG=true` to push images to registry after building
PUSH_REG ?= false

# We use a conditional (true on any non-empty string) later. To avoid
# accidents, we don't use user-controlled PUSH_REG directly.
# See: https://www.gnu.org/software/make/manual/html_node/Conditional-Functions.html
_condition_push :=
ifeq ($(PUSH_REG), true)
	_condition_push := not_empty_so_true
endif

# Use `make devdocs FUNCTIONDOCS=true` to build the function documentation
FUNCTIONDOCS ?= false

_autosummary_flags := --define autosummary_generate=0
ifeq ($(FUNCTIONDOCS), true)
	_autosummary_flags :=
endif

help:
	@echo "Available commands to 'make':"
	@echo "  set-version          : set version (e.g set-version FLAGS=\"--version 2.0.0 --build 0 --spec alpha\")"
	@echo "  uninstall            : uninstall all vantage6 packages"
	@echo "  install              : do a regular install of all vantage6 packages"
	@echo "  install-dev          : do an editable install of all vantage6 packages"
	@echo "  image                : build the node/server docker image"
	@echo "  algorithm-store-image: build the algorithm store docker image"
	@echo "  ui-image             : build the user interface docker image"
	@echo "  base-image           : build the infrastructure base image"
	@echo "  algorithm-base-image : build the algorithm base image"
	@echo "  support-image        : build the supporing images"
	@echo "  rebuild              : rebuild all python packages"
	@echo "  publish              : publish built python packages to pypi.org (BE CAREFUL!)"
	@echo "  community            : notify community FLAGS="--version 99.99.88 --notes 'I should have done more!' --post-notes 'Oh.. Maybe not'""
	@echo "  test                 : run all unittests and compute coverage"
	@echo "  devdocs              : run a documentation development server"
	@echo ""
	@echo "Using "
	@echo "  tag:       ${TAG}"
	@echo "  registry:  ${REGISTRY}"
	@echo "  base:      ${BASE}"
	@echo "  platforms: ${PLATFORMS}"

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
	pip uninstall -y vantage6-algorithm-tools
	pip uninstall -y vantage6-common
	pip uninstall -y vantage6-node
	pip uninstall -y vantage6-backend-common
	pip uninstall -y vantage6-server
	pip uninstall -y vantage6-algorithm-store

install:
	cd vantage6-common && pip install .
	cd vantage6-client && pip install .
	cd vantage6-algorithm-tools && pip install .
	cd vantage6 && pip install .
	cd vantage6-node && pip install .
	cd vantage6-backend-common && pip install .
	cd vantage6-server && pip install .
	cd vantage6-algorithm-store && pip install .

install-dev:
	cd vantage6-common && pip install -e .
	cd vantage6-client && pip install -e .
	cd vantage6-algorithm-tools && pip install -e .
	cd vantage6 && pip install -e .[dev]
	cd vantage6-node && pip install -e .[dev]
	cd vantage6-backend-common && pip install -e .[dev]
	cd vantage6-server && pip install -e .[dev]
	cd vantage6-algorithm-store && pip install -e .[dev]

base-image:
	@echo "Building ${REGISTRY}/infrastructure/infrastructure-base:${TAG}"
	@echo "Building ${REGISTRY}/infrastructure/infrastructure-base:latest"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/infrastructure-base:${TAG} \
		--tag ${REGISTRY}/infrastructure/infrastructure-base:latest \
		--platform ${PLATFORMS} \
		-f ./docker/infrastructure-base.Dockerfile \
		$(if ${_condition_push},--push .,.)

algorithm-base-image:
	@echo "Building ${REGISTRY}/algorithms/algorithm-base:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/algorithm-base:${TAG} \
		--tag ${REGISTRY}/infrastructure/algorithm-base:latest \
		--platform ${PLATFORMS} \
		--build-arg TAG=${TAG} \
		-f ./docker/algorithm-base.Dockerfile \
		$(if ${_condition_push},--push .,.)

# FIXME FM 17-10-2023: This fails to build for arm64, this is because of
# the r-base image.
algorithm-omop-base-image:
	@echo "Building ${REGISTRY}/algorithms/algorithm-ohdsi-base:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/algorithm-ohdsi-base:${TAG} \
		--tag ${REGISTRY}/infrastructure/algorithm-ohdsi-base:latest \
		--build-arg BASE=${BASE} \
		--build-arg TAG=${TAG} \
		--platform linux/amd64 \
		-f ./docker/algorithm-ohdsi-base.Dockerfile \
		$(if ${_condition_push},--push .,.)

support-image:
	@echo "Building support images"
	@echo "All support images are also tagged with `latest`"
	make support-alpine-image
	make support-vpn-client-image
	make support-vpn-configurator-image
	make support-ssh-tunnel-image
	make support-squid-image

support-squid-image:
	@echo "Building ${REGISTRY}/infrastructure/squid:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/squid:${TAG} \
		--tag ${REGISTRY}/infrastructure/squid:latest \
		--platform ${PLATFORMS} \
		-f ./docker/squid.Dockerfile \
		$(if ${_condition_push},--push .,.)

support-alpine-image:
	@echo "Building ${REGISTRY}/infrastructure/alpine:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/alpine:${TAG} \
		--tag ${REGISTRY}/infrastructure/alpine:latest \
		--platform ${PLATFORMS} \
		-f ./docker/alpine.Dockerfile \
		$(if ${_condition_push},--push .,.)

support-vpn-client-image:
	@echo "Building ${REGISTRY}/infrastructure/vpn-client:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/vpn-client:${TAG} \
		--tag ${REGISTRY}/infrastructure/vpn-client:latest \
		--platform ${PLATFORMS} \
		-f ./docker/vpn-client.Dockerfile \
		$(if ${_condition_push},--push .,.)

support-vpn-configurator-image:
	@echo "Building ${REGISTRY}/infrastructure/vpn-configurator:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/vpn-configurator:${TAG} \
		--tag ${REGISTRY}/infrastructure/vpn-configurator:latest \
		--platform ${PLATFORMS} \
		-f ./docker/vpn-configurator.Dockerfile \
		$(if ${_condition_push},--push .,.)

support-ssh-tunnel-image:
	@echo "Building ${REGISTRY}/infrastructure/ssh-tunnel:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/ssh-tunnel:${TAG} \
		--tag ${REGISTRY}/infrastructure/ssh-tunnel:latest \
		--platform ${PLATFORMS} \
		-f ./docker/ssh-tunnel.Dockerfile \
		$(if ${_condition_push},--push .,.)

image:
	@echo "Building ${REGISTRY}/infrastructure/node:${TAG}"
	@echo "Building ${REGISTRY}/infrastructure/server:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/node:${TAG} \
		--tag ${REGISTRY}/infrastructure/server:${TAG} \
		--build-arg TAG=${TAG} \
		--build-arg BASE=${BASE} \
		--platform ${PLATFORMS} \
		-f ./docker/node-and-server.Dockerfile \
		$(if ${_condition_push},--push .,.)

algorithm-store-image:
	@echo "Building ${REGISTRY}/infrastructure/algorithm-store:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/algorithm-store:${TAG} \
		--tag ${REGISTRY}/infrastructure/algorithm-store:latest \
		--build-arg TAG=${TAG} \
		--build-arg BASE=${BASE} \
		--platform ${PLATFORMS} \
		-f ./docker/algorithm-store.Dockerfile \
		$(if ${_condition_push},--push .,.)

ui-image:
	@echo "Building ${REGISTRY}/infrastructure/ui:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/infrastructure/ui:${TAG} \
		--tag ${REGISTRY}/infrastructure/ui:latest \
		--build-arg TAG=${TAG} \
		--build-arg BASE=${BASE} \
		--platform ${PLATFORMS} \
		-f ./docker/ui.Dockerfile \
		$(if ${_condition_push},--push .,.)

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
	@echo "         VANTAGE6 ALGORITHM TOOLS   "
	@echo "------------------------------------"
	cd vantage6-algorithm-tools && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 CLI            "
	@echo "------------------------------------"
	cd vantage6 && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 NODE            "
	@echo "------------------------------------"
	cd vantage6-node && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 BACKEND COMMON    "
	@echo "------------------------------------"
	cd vantage6-backend-common && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 SERVER            "
	@echo "------------------------------------"
	cd vantage6-server && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 ALGORITHM STORE   "
	@echo "------------------------------------"
	cd vantage6-algorithm-store && make rebuild

publish:
	cd vantage6-common && make publish
	cd vantage6-client && make publish
	cd vantage6-algorithm-tools && make publish
	cd vantage6 && make publish
	cd vantage6-node && make publish
	cd vantage6-backend-common && make publish
	cd vantage6-server && make publish
	cd vantage6-algorithm-store && make publish

test:
	coverage run --source=vantage6 --omit="utest.py","*.html","*.htm","*.txt","*.yml","*.yaml" utest.py

# the READTHEDOCS envvar is set for this target to circumvent a monkey patch
# that would get stuck indefinitely when running the sphinx-autobuild package.
# Note that the value of the envvar does not matter, just that it is set.
devdocs: export READTHEDOCS = Yes
devdocs:
	sphinx-autobuild docs docs/_build/html --watch . ${_autosummary_flags}