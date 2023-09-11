FROM python:3.7-slim-buster

LABEL version="1"
LABEL infrastructure_version = "2"
LABEL maintainer="Frank Martin <f.martin@iknl.nl>"

# slim buster does not have gcc installed
RUN apt-get update \
    && apt-get install -y gcc python3-dev

# COPY vantage6/requirements.txt /tmp/cli-requirements.txt
# COPY vantage6-client/requirements.txt /tmp/client-requirements.txt
# COPY vantage6-common/requirements.txt /tmp/common-requirements.txt
# COPY vantage6-node/requirements.txt /tmp/node-requirements.txt
COPY vantage6-server/requirements.txt /tmp/server-requirements.txt

# RUN pip install -r /tmp/cli-requirements.txt
# RUN pip install -r /tmp/client-requirements.txt
# RUN pip install -r /tmp/common-requirements.txt
# RUN pip install -r /tmp/node-requirements.txt
RUN pip install -r /tmp/server-requirements.txt