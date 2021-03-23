FROM harbor.vantage6.ai/infrastructure/base

LABEL version="2.0"
LABEL infrastructure_version = "2.0.0"
LABEL maintainer="Frank Martin <f.martin@iknl.nl>, Melle Sieswerda <m.sieswerda@iknl.nl>"

# Enable SSH access in Azure App service
RUN apt update -y
RUN apt upgrade -y
RUN apt install openssh-server sudo -y
RUN useradd -rm -d /home/ubuntu -s /bin/bash -g root -G sudo -u 1000 test
RUN  echo 'root:Docker!' | chpasswd
COPY sshd_config /etc/ssh/
RUN mkdir /run/sshd

# Fix DB issue
RUN apt install python-psycopg2 -y
RUN pip install psycopg2-binary

# install vantage from source
COPY . /vantage6
RUN pip install -e /vantage6/vantage6-common
RUN pip install -e /vantage6/vantage6-client
RUN pip install -e /vantage6/vantage6
RUN pip install -e /vantage6/vantage6-node
RUN pip install -e /vantage6/vantage6-server

# Greenlet fixes: see https://github.com/gevent/gevent/issues/1260
# RUN pip install gunicorn==19.9.0
RUN pip install gevent==1.3.4
RUN pip install greenlet==0.4.13

# socketio fixes untill we remove the socketIO_client package from the node
RUN pip install python-engineio==3.10.0
RUN pip install python-socketio==4.4.0


# expose the proxy server port
ARG port=80
EXPOSE ${port} 2222
ENV PROXY_SERVER_PORT ${port}
