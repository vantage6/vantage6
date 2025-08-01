# Dockerfile for the algorithm store
#
# IMAGE
# -----
# * harbor2.vantage6.ai/infrastructure/algorithm-store:x.x.x
#
ARG TAG=latest
ARG BASE=5.0
FROM harbor2.vantage6.ai/infrastructure/infrastructure-base:${BASE}

LABEL version=${TAG}
LABEL maintainer="Frank Martin <f.martin@iknl.nl>; Bart van Beusekom <b.vanbeusekom@iknl.nl>"

RUN apt update -y
RUN apt upgrade -y

# Fix DB issue
RUN pip install psycopg2-binary

# copy source
COPY . /vantage6

RUN pip install --upgrade pip

# Install requirements. We cannot rely on setup.py because of the way
# python resolves package versions. To control all dependencies we install
# them from the requirements.txt
# This is also done in the base-image to safe build time. We redo it here
# to allow for dependency upgrades in minor and patch versions.
RUN pip install -r /vantage6/requirements.txt \
  --extra-index-url https://www.piwheels.org/simple

# install individual packages
RUN pip install -e /vantage6/vantage6-common
RUN pip install -e /vantage6/vantage6-client
RUN pip install -e /vantage6/vantage6
RUN pip install -e /vantage6/vantage6-backend-common
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
