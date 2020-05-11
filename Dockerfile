FROM harbor.distributedlearning.ai/infrastructure/base

LABEL version="0.0.1"
LABEL infrastructure_version = "1.0.0"
LABEL maintainer="Frank Martin <f.martin@iknl.nl>, Melle Sieswerda <m.sieswerda@iknl.nl>"

COPY . /vantage6
RUN pip install -e /vantage6/vantage6-common
RUN pip install -e /vantage6/vantage6-client
RUN pip install -e /vantage6/vantage6
RUN pip install -e /vantage6/vantage6-node
RUN pip install -e /vantage6/vantage6-server

# copy start file to app folder

# expose the proxy server port
ARG port=80
EXPOSE ${port}
ENV PROXY_SERVER_PORT ${port}
