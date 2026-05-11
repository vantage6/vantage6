# Dockerfile for the algorithm store
#
# IMAGE
# -----
# * ghcr.io/vantage6/infrastructure/algorithm-store:x.x.x
#
ARG BASE=4.15
ARG REGISTRY=ghcr.io/vantage6/infrastructure
FROM ${REGISTRY}/infrastructure-base:${BASE}

ARG TAG=latest
LABEL version=${TAG}
LABEL maintainer="Frank Martin <f.martin@iknl.nl>; Bart van Beusekom <b.vanbeusekom@iknl.nl>"

RUN apt-get update -y \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Fix DB issue
RUN pip install psycopg2-binary

# copy source
COPY . /vantage6

# install individual packages
# TODO check which dependencies are needed - remove at least server
RUN pip install -e /vantage6/vantage6-common
RUN pip install -e /vantage6/vantage6-client
RUN pip install -e /vantage6/vantage6
RUN pip install -e /vantage6/vantage6-backend-common
RUN pip install -e /vantage6/vantage6-algorithm-store

# Overwrite uWSGI installation from the requirements.txt
# Install uWSGI from source (for RabbitMQ)
RUN apt-get update \
  && apt-get install --no-install-recommends --no-install-suggests -y \
  libssl-dev python3-setuptools \
  && rm -rf /var/lib/apt/lists/*
RUN CFLAGS="-I/usr/local/opt/openssl/include" \
  LDFLAGS="-L/usr/local/opt/openssl/lib" \
  UWSGI_PROFILE_OVERRIDE=ssl=true \
  pip install uwsgi -Iv

RUN chmod +x /vantage6/vantage6-algorithm-store/server.sh
