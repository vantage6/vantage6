# Dockerfile for the node an server images
#
# IMAGES
# ------
# * harbor2.vantage6.ai/infrastructure/node:x.x.x
# * harbor2.vantage6.ai/infrastructure/server:x.x.x
#
ARG TAG=latest
ARG BASE=5.0
FROM harbor2.vantage6.ai/infrastructure/infrastructure-base:${BASE}

LABEL version=${TAG}
LABEL maintainer="Frank Martin <f.martin@iknl.nl>"

# Update and upgrade
RUN apt update -y
RUN apt upgrade -y

# Install uv
RUN pip install uv

# copy source
COPY . /vantage6

# Install dependencies using uv
WORKDIR /vantage6

# Create virtual environment and install all packages in editable mode
RUN uv venv

# Install all packages in editable mode
RUN uv pip install -e vantage6-common
RUN uv pip install -e vantage6-client
RUN uv pip install -e vantage6
RUN uv pip install -e vantage6-backend-common
RUN uv pip install -e vantage6-server
RUN uv pip install -e vantage6-node

# Overwrite uWSGI installation from the requirements.txt
# Install uWSGI from source (for RabbitMQ)
RUN apt-get install --no-install-recommends --no-install-suggests -y \
  libssl-dev python3-setuptools
RUN CFLAGS="-I/usr/local/opt/openssl/include" \
  LDFLAGS="-L/usr/local/opt/openssl/lib" \
  UWSGI_PROFILE_OVERRIDE=ssl=true \
  uv pip install --no-binary uwsgi uwsgi

RUN chmod +x /vantage6/vantage6-server/server.sh

# expose the proxy server port
ARG port=80
EXPOSE ${port}
ENV PROXY_SERVER_PORT=${port}
