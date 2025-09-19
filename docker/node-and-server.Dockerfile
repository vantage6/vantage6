# Dockerfile for the node an server images
#
# IMAGES
# ------
# * harbor2.vantage6.ai/infrastructure/node:x.x.x
# * harbor2.vantage6.ai/infrastructure/server:x.x.x
#
ARG TAG=latest
ARG BASE=5.0
FROM ghcr.io/astral-sh/uv:python3.13-bookworm

LABEL version=${TAG}
LABEL maintainer="Frank Martin <f.martin@iknl.nl>"

# slim bookworm does not have gcc installed
# libdev is needed for arm compilation
RUN apt-get update \
    && apt-get install --no-install-recommends -y gcc python3-dev libffi-dev \
    && apt-get upgrade -y

# Fix DB issue
RUN pip install psycopg2-binary

# copy source
COPY . /vantage6

# Install dependencies using uv
WORKDIR /vantage6

# Install all packages in editable mode globally
RUN uv pip install --system -e vantage6-common
RUN uv pip install --system -e vantage6-client
RUN uv pip install --system -e vantage6
RUN uv pip install --system -e vantage6-backend-common
RUN uv pip install --system -e vantage6-server
RUN uv pip install --system -e vantage6-node

# Install Gunicorn application server
RUN uv pip install --system gunicorn

RUN chmod +x /vantage6/vantage6-server/server.sh

# expose the proxy server port
ARG port=80
EXPOSE ${port}
ENV PROXY_SERVER_PORT=${port}
