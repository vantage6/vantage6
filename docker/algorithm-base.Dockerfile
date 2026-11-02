FROM python:3.10-slim-bookworm

LABEL version=${TAG}
LABEL maintainer="F.C. Martin <f.martin@iknl.nl>"

# we need to copy the readme for the setup.py from the vantage6-algorithm-tools
# as it uses the top-level readme.
COPY ./README.md /README.md
COPY ./vantage6-common /vantage6-common
COPY ./vantage6-algorithm-tools /vantage6-algorithm-tools

RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# pip < 26.2.2 trusts the compromised eMudhra CAs, so install it from a hash-pinned URL
RUN pip install "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
RUN pip install /vantage6-common
RUN pip install /vantage6-algorithm-tools