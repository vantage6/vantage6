# Dockerfile for the node an server images
#
# IMAGES
# ------
# * harbor2.vantage6.ai/infrastructure/node:x.x.x
# * harbor2.vantage6.ai/infrastructure/server:x.x.x
#
FROM python:3.10-slim-buster

ARG TAG=latest

LABEL version=${TAG}
LABEL maintainer="Frank Martin <f.martin@iknl.nl>"

# Update and upgrade
RUN apt-get update -y && apt-get upgrade -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# copy source
COPY vantage6-common /vantage6/vantage6-common
COPY vantage6-client /vantage6/vantage6-client
COPY vantage6-algorithm-tools /vantage6/vantage6-algorithm-tools
COPY vantage6 /vantage6/vantage6
COPY vantage6-node /vantage6/vantage6-node
COPY requirements.txt README.md /vantage6

# Install requirements. We cannot rely on setup.py because of the way
# python resolves package versions. To control all dependencies we install
# them from the requirements.txt
# This is also done in the base-image to safe build time. We redo it here
# to allow for dependency upgrades in minor and patch versions.
RUN pip install -r /vantage6/requirements.txt \
  --extra-index-url https://www.piwheels.org/simple
RUN ls -la /vantage6
# install individual packages
RUN pip install -e /vantage6/vantage6-common \
                -e /vantage6/vantage6-client \
                -e /vantage6/vantage6-algorithm-tools \
                -e /vantage6/vantage6 \
                -e /vantage6/vantage6-node

# expose the proxy server port
ARG port=80
EXPOSE ${port}
ENV PROXY_SERVER_PORT=${port}
