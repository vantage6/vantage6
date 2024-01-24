# Dockerfile for the algorithm store
#
# IMAGE
# -----
# * harbor2.vantage6.ai/infrastructure/algorithm-store:x.x.x
#
ARG TAG=latest
ARG BASE=4.1
FROM harbor2.vantage6.ai/infrastructure/infrastructure-base:${BASE}

LABEL version=${TAG}
LABEL maintainer="Frank Martin <f.martin@iknl.nl>; Bart van Beusekom <b.vanbeusekom@iknl.nl>"

RUN apt update -y
RUN apt upgrade -y

# copy source
COPY . /vantage6

# install individual packages
RUN pip install -e /vantage6/vantage6-common
RUN pip install -e /vantage6/vantage6
# TODO remove dependency on server?
RUN pip install -e /vantage6/vantage6-server
RUN pip install -e /vantage6/vantage6-algorithm-store

# Overwrite uWSGI installation from the requirements.txt
# Install uWSGI from source (for RabbitMQ)
RUN apt-get install --no-install-recommends --no-install-suggests -y \
  libssl-dev python3-setuptools
RUN CFLAGS="-I/usr/local/opt/openssl/include" \
  LDFLAGS="-L/usr/local/opt/openssl/lib" \
  UWSGI_PROFILE_OVERRIDE=ssl=true \
  pip install uwsgi -Iv

RUN chmod +x /vantage6/vantage6-algorithm-store/server.sh
