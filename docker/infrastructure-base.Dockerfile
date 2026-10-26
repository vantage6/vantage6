FROM python:3.10-slim-bookworm

LABEL version="4.15"
LABEL maintainer="Frank Martin <f.martin@iknl.nl>"

# slim bookworm does not have gcc installed
# libdev is needed for arm compilation
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y gcc python3-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# pip < 26.2.2 trusts the compromised eMudhra CAs, so install it from a hash-pinned URL
RUN pip install "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"

# install requirements. We cannot rely on setup.py because of the way
# python resolves package versions. To control all dependencies we install
# them from the requirements.txt
COPY requirements.txt /vantage6/requirements.txt
RUN pip install -r /vantage6/requirements.txt \
    --extra-index-url https://www.piwheels.org/simple

# Removed individual requirements files. Not sure if we want to keep
# this at project level or in the packages themselfs.

# Copy all project dependencies into the image
# COPY vantage6/requirements.txt /tmp/cli-requirements.txt
# COPY vantage6-client/requirements.txt /tmp/client-requirements.txt
# COPY vantage6-algorithm-tools/requirements.txt /tmp/tools-requirements.txt
# COPY vantage6-common/requirements.txt /tmp/common-requirements.txt
# COPY vantage6-node/requirements.txt /tmp/node-requirements.txt
# COPY vantage6-server/requirements.txt /tmp/server-requirements.txt

# installs dependencies. The extra index url is used for pre-build ARM wheels
# to improve ARM build speed.
# RUN pip install -r /tmp/cli-requirements.txt \
#     --extra-index-url https://www.piwheels.org/simple
# RUN pip install -r /tmp/client-requirements.txt \
#     --extra-index-url https://www.piwheels.org/simple
# RUN pip install -r /tmp/tools-requirements.txt \
#     --extra-index-url https://www.piwheels.org/simple
# RUN pip install -r /tmp/common-requirements.txt \
#     --extra-index-url https://www.piwheels.org/simple
# RUN pip install -r /tmp/node-requirements.txt \
#     --extra-index-url https://www.piwheels.org/simple
# RUN pip install -r /tmp/server-requirements.txt \
#     --extra-index-url https://www.piwheels.org/simple