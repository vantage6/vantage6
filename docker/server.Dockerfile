# Dockerfile for the server image
#
# The server runtime does not need the full vantage6 CLI package, so we install
# only the common, backend-common, and server packages.
#
# IMAGE
# -----
# * ghcr.io/vantage6/infrastructure/server:x.x.x
#

# Builder image
# python:3.10-slim-bookworm multi-platform image index:
# https://hub.docker.com/layers/library/python/3.10-slim-bookworm/images/sha256-9643927a6fc74bd81b0f1bbb5cce3cb4a491f46b4c5dbee770f28e575f180015
FROM docker.io/library/python@sha256:9643927a6fc74bd81b0f1bbb5cce3cb4a491f46b4c5dbee770f28e575f180015 AS builder


# Keep image layers smaller
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# We build uWSGI and any source-only dependencies separately so the compiler
# and headers do not end up in the server image.
RUN apt-get update \
    && apt-get install --no-install-recommends --no-install-suggests -y \
        gcc \
        libc6-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /vantage6

COPY README.md /vantage6/README.md
COPY vantage6-common /vantage6/vantage6-common
COPY vantage6-backend-common /vantage6/vantage6-backend-common
COPY vantage6-server /vantage6/vantage6-server

# The standard server image uses PostgreSQL, so we install the server with its
# PostgreSQL driver extra.
# Vantage6's goal was to be more DB agnostic. But this is not free, so maybe
# it's best to be "opinionated" at the moment and make sure we support
# postgres.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install \
        -e /vantage6/vantage6-common \
        -e /vantage6/vantage6-backend-common \
        -e "/vantage6/vantage6-server[postgres]" \
    && CFLAGS="-I/usr/local/opt/openssl/include" \
        LDFLAGS="-L/usr/local/opt/openssl/lib" \
        UWSGI_PROFILE_OVERRIDE=ssl=true \
        /opt/venv/bin/pip install uwsgi==2.0.31


# Server image
# python:3.10-slim-bookworm multi-platform image index:
# https://hub.docker.com/layers/library/python/3.10-slim-bookworm/images/sha256-9643927a6fc74bd81b0f1bbb5cce3cb4a491f46b4c5dbee770f28e575f180015
FROM docker.io/library/python@sha256:9643927a6fc74bd81b0f1bbb5cce3cb4a491f46b4c5dbee770f28e575f180015

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /vantage6

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /vantage6 /vantage6

# server.sh starts uWSGI on port 80.
EXPOSE 80
