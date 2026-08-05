# Dockerfile for the node image
#
# The node runtime does not need the full vantage6 CLI package, so we install
# only the common and node packages.
#
# IMAGE
# -----
# * ghcr.io/vantage6/infrastructure/node:x.x.x
#

# python:3.10-slim-bookworm multi-platform image index:
# https://hub.docker.com/layers/library/python/3.10-slim-bookworm/images/sha256-9643927a6fc74bd81b0f1bbb5cce3cb4a491f46b4c5dbee770f28e575f180015
FROM docker.io/library/python@sha256:9643927a6fc74bd81b0f1bbb5cce3cb4a491f46b4c5dbee770f28e575f180015 AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# Some dependencies need to be compiled on arm64. We build them here so the
# compiler and headers do not end up in the node image.
RUN apt-get update \
    && apt-get install --no-install-recommends --no-install-suggests -y \
        gcc \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /vantage6

COPY README.md /vantage6/README.md
COPY vantage6-common /vantage6/vantage6-common
COPY vantage6-node /vantage6/vantage6-node

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install \
        -e /vantage6/vantage6-common \
        -e /vantage6/vantage6-node

# python:3.10-slim-bookworm multi-platform image index:
# https://hub.docker.com/layers/library/python/3.10-slim-bookworm/images/sha256-9643927a6fc74bd81b0f1bbb5cce3cb4a491f46b4c5dbee770f28e575f180015
FROM docker.io/library/python@sha256:9643927a6fc74bd81b0f1bbb5cce3cb4a491f46b4c5dbee770f28e575f180015

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /vantage6

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /vantage6 /vantage6
