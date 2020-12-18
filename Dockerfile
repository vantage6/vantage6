FROM harbor.vantage6.ai/infrastructure/base

LABEL version="1.0"
LABEL infrastructure_version = "1.2.3"
LABEL maintainer="Frank Martin <f.martin@iknl.nl>, Melle Sieswerda <m.sieswerda@iknl.nl>"

COPY . /vantage6
RUN pip install -e /vantage6/vantage6-common
RUN pip install -e /vantage6/vantage6-client
RUN pip install -e /vantage6/vantage6
RUN pip install -e /vantage6/vantage6-node
RUN pip install -e /vantage6/vantage6-server

# Greenlet fixes: see https://github.com/gevent/gevent/issues/1260
# RUN pip install gunicorn==19.9.0
# RUN pip install gevent==1.3.4
RUN pip install greenlet==0.4.13

# expose the proxy server port
ARG port=80
EXPOSE ${port}
ENV PROXY_SERVER_PORT ${port}
