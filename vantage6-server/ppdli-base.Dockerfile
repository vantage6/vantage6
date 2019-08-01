FROM python:3.7

LABEL version="0.0.1"
LABEL infrastructure_version = "0.3.0"
LABEL maintainer="Frank Martin <f.martin@iknl.nl>"

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt
