# `make` is expected to be called from the directory that contains
# this Makefile

# docker image tag
TAG ?= uluru
REGISTRY ?= ghcr.io/vantage6/infrastructure
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
_condition_tag_latest :=
ifeq ($(TAG_LATEST), true)
	_condition_tag_latest := not_empty_so_true
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
	@echo "  uninstall            : remove the local virtual environment"
	@echo "  lock                 : update uv.lock from local pyproject.toml files"
	@echo "  lock-upgrade         : update uv.lock and upgrade dependency versions"
	@echo "  install              : install local packages (non-editable) from uv.lock"
	@echo "  install-dev          : editable install of all workspace packages from uv.lock"
	@echo "  install-pypi         : install published packages from PyPI (VERSION=5.0.0)"
	@echo "  image                : build the node/hq docker image"
	@echo "  algorithm-store-image: build the algorithm store docker image"
	@echo "  ui-image             : build the user interface docker image"
	@echo "  base-image           : build the infrastructure base image"
	@echo "  algorithm-base-image : build the algorithm base image"
	@echo "  support-image        : build the supporing images"
	@echo "  mirror-images        : re-publish third-party support images to our registry"
	@echo "  rebuild              : rebuild all python packages"
	@echo "  publish              : publish built python packages to pypi.org (BE CAREFUL!)"
	@echo "  test                 : run all unittests and compute coverage"
	@echo "  install-docs         : install documentation dependencies"
	@echo "  devdocs              : run documentation locally with live reload"
	@echo ""
	@echo "Using "
	@echo "  tag:       ${TAG}"
	@echo "  registry:  ${REGISTRY}"
	@echo "  base:      ${BASE}"
	@echo "  platforms: ${PLATFORMS}"

set-version:
	cd tools && python update-version.py ${FLAGS}

# Match package versions in each subpackage pyproject.toml when installing from PyPI.
VERSION ?= 5.0.0

uninstall:
	rm -rf .venv

lock:
	uv lock

lock-upgrade:
	uv lock --upgrade

# Non-editable install of local workspace packages (uses uv.lock).
install:
	uv sync --no-editable

# Editable install of local workspace packages (uses uv.lock). Run `make lock` after
# changing dependencies in any pyproject.toml.
install-dev:
	uv sync --extra dev --extra docs

# Install published wheels from PyPI (simulates end-user / post-release environment).
install-pypi:
	uv pip install \
		"vantage6-common==$(VERSION)" \
		"vantage6-client==$(VERSION)" \
		"vantage6-algorithm-tools==$(VERSION)" \
		"vantage6==$(VERSION)" \
		"vantage6-node==$(VERSION)" \
		"vantage6-backend-common==$(VERSION)" \
		"vantage6-hq==$(VERSION)" \
		"vantage6-algorithm-store==$(VERSION)"
	uv pip install ".[dev,docs]"

algorithm-base-image:
	@echo "Building ${REGISTRY}/algorithm-base:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/algorithm-base:${TAG} \
		$(if ${_condition_tag_latest},--tag ${REGISTRY}/algorithm-base:latest) \
		--platform ${PLATFORMS} \
		--build-arg TAG=${TAG} \
		-f ./docker/algorithm-base.Dockerfile \
		$(if ${_condition_push},--push .,.)

# FIXME FM 17-10-2023: This fails to build for arm64, this is because of
# the r-base image.
algorithm-omop-base-image:
	@echo "Building ${REGISTRY}/algorithm-ohdsi-base:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/algorithm-ohdsi-base:${TAG} \
		$(if ${_condition_tag_latest},--tag ${REGISTRY}/algorithm-ohdsi-base:latest) \
		--build-arg BASE=${BASE} \
		--build-arg TAG=${TAG} \
		--build-arg REGISTRY=${REGISTRY} \
		--platform linux/amd64 \
		-f ./docker/algorithm-ohdsi-base.Dockerfile \
		$(if ${_condition_push},--push .,.)

support-image:
	@echo "Building support images"
	@echo "All support images are also tagged with 'latest'"
	make support-alpine-image

support-alpine-image:
	@echo "Building ${REGISTRY}/alpine:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/alpine:${TAG} \
		$(if ${_condition_tag_latest},--tag ${REGISTRY}/alpine:latest) \
		--platform ${PLATFORMS} \
		-f ./docker/alpine.Dockerfile \
		$(if ${_condition_push},--push .,.)

# Copy the third-party support images listed in docker/mirror-images.txt
mirror-images:
	@echo "Re-publishing third-party images into ${REGISTRY} as :${TAG}"
	REGISTRY=${REGISTRY} TAG=${TAG} PUSH_REG=${PUSH_REG} ./tools/mirror-images.sh

image:
	@echo "Building ${REGISTRY}/node:${TAG}"
	@echo "Building ${REGISTRY}/hq:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/node:${TAG} \
		--tag ${REGISTRY}/hq:${TAG} \
		$(if ${_condition_tag_latest},--tag ${REGISTRY}/node:latest) \
		$(if ${_condition_tag_latest},--tag ${REGISTRY}/hq:latest) \
		--build-arg TAG=${TAG} \
		--build-arg BASE=${BASE} \
		--build-arg REGISTRY=${REGISTRY} \
		--platform ${PLATFORMS} \
		-f ./docker/node-and-hq.Dockerfile \
		$(if ${_condition_push},--push .,.)

algorithm-store-image:
	@echo "Building ${REGISTRY}/algorithm-store:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/algorithm-store:${TAG} \
		$(if ${_condition_tag_latest},--tag ${REGISTRY}/algorithm-store:latest) \
		--build-arg TAG=${TAG} \
		--build-arg BASE=${BASE} \
		--build-arg REGISTRY=${REGISTRY} \
		--platform ${PLATFORMS} \
		-f ./docker/algorithm-store.Dockerfile \
		$(if ${_condition_push},--push .,.)

ui-image:
	@echo "Building ${REGISTRY}/ui:${TAG}"
	docker buildx build \
		--tag ${REGISTRY}/ui:${TAG} \
		$(if ${_condition_tag_latest},--tag ${REGISTRY}/ui:latest) \
		--build-arg TAG=${TAG} \
		--platform ${PLATFORMS} \
		-f ./docker/ui.Dockerfile \
		$(if ${_condition_push},--push .,.)

rebuild:
	-rm -rf dist
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
	@echo "         VANTAGE6 HQ                "
	@echo "------------------------------------"
	cd vantage6-hq && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 ALGORITHM STORE   "
	@echo "------------------------------------"
	cd vantage6-algorithm-store && make rebuild

publish:
	# uv workspace builds write artifacts to the root dist/ directory
	twine upload --repository pypi dist/*

# Default test subpackages if none specified
TEST_SUBPACKAGES ?= common,cli,algorithm-store,hq,algorithm-tools

test:
	export TEST_ARGS=$(echo $(TEST_SUBPACKAGES) | tr ',' ' ' | sed 's/^/--/;s/ / --/g')
	coverage run --source=./vantage6-$(subst ,/,$(TEST_SUBPACKAGES)) --omit="utest.py","*.html","*.htm","*.txt","*.yml","*.yaml" utest.py $(TEST_ARGS)

install-docs:
	uv sync --extra docs

# the READTHEDOCS envvar is set for this target to circumvent a monkey patch
# that would get stuck indefinitely when running the sphinx-autobuild package.
# Note that the value of the envvar does not matter, just that it is set.
# Also, note that --ignore option is used to ignore directories that are not
# relevant for the documentation build.
devdocs: export READTHEDOCS = Yes
devdocs:
	sphinx-autobuild docs docs/_build/html \
		--ignore dev/ \
		--ignore .github/ \
		--ignore .devspace/ \
		--ignore .venv/ \
		${_autosummary_flags}