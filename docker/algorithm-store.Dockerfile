# Dockerfile for the algorithm store
#
# IMAGE
# -----
# * harbor2.vantage6.ai/infrastructure/algorithm-store:x.x.x
#
ARG TAG=latest
ARG BASE=5.0
FROM ghcr.io/astral-sh/uv:python3.13-bookworm

LABEL version=${TAG}
LABEL maintainer="Frank Martin <f.martin@iknl.nl>; Bart van Beusekom <b.vanbeusekom@iknl.nl>"
  
# slim bookworm does not have gcc installed
# libdev is needed for arm compilation
RUN apt-get update \
    && apt-get install -y gcc python3-dev libffi-dev \
    && apt-get upgrade -y

# Fix DB issue
RUN pip install psycopg2-binary

# copy source
COPY . /vantage6

# Install dependencies using uv
WORKDIR /vantage6

# Install local packages in editable mode globally
RUN uv pip install --system -e vantage6-common
RUN uv pip install --system -e vantage6-client
RUN uv pip install --system -e vantage6
RUN uv pip install --system -e vantage6-backend-common
RUN uv pip install --system -e vantage6-algorithm-store

# Overwrite uWSGI installation from the requirements.txt
# Install uWSGI from source (for RabbitMQ)
RUN apt-get install --no-install-recommends --no-install-suggests -y \
  libssl-dev python3-setuptools
RUN CFLAGS="-I/usr/local/opt/openssl/include" \
  LDFLAGS="-L/usr/local/opt/openssl/lib" \
  UWSGI_PROFILE_OVERRIDE=ssl=true \
  uv pip install --system --no-binary=uwsgi uwsgi

RUN chmod +x /vantage6/vantage6-algorithm-store/server.sh
