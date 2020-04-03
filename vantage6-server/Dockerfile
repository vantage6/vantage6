# poc that we can dockerize the node-instance
FROM harbor.distributedlearning.ai/infrastructure/base

LABEL version="0.0.1"
LABEL infrastructure_version = "1.0.0"
LABEL maintainer="Frank Martin <f.martin@iknl.nl>"

COPY . /vantage6
RUN pip install -e /vantage6/vantage6
RUN pip install -e /vantage6/vantage6-common
RUN pip install -e /vantage6/vantage6-client
RUN pip install -e /vantage6/vantage6-server

ENTRYPOINT ["vserver-local", "start", "--config"]