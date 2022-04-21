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

# Install uWSGI from source (for RabbitMQ)
RUN apt-get install --no-install-recommends --no-install-suggests -y \
  libssl-dev python3-setuptools
RUN CFLAGS="-I/usr/local/opt/openssl/include" \
  LDFLAGS="-L/usr/local/opt/openssl/lib" \
  UWSGI_PROFILE_OVERRIDE=ssl=true \
  pip install uwsgi -Iv

# install vantage from source
COPY . /vantage6
RUN pip install -e /vantage6/vantage6-common
RUN pip install -e /vantage6/vantage6-client
RUN pip install -e /vantage6/vantage6
RUN pip install -e /vantage6/vantage6-node
RUN pip install -e /vantage6/vantage6-server

# Greenlet fixes: see https://github.com/gevent/gevent/issues/1260
# RUN pip install gunicorn==19.9.0
# RUN pip install gevent==20.9.0
# RUN pip install greenlet==0.4.13

# socketio fixes untill we remove the socketIO_client package from the node
# RUN pip install python-engineio==3.10.0
# RUN pip install python-socketio==4.4.0

# Add docker-compose-wait tool -------------------
ENV WAIT_VERSION 2.7.2
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/$WAIT_VERSION/wait /wait
RUN chmod +x /wait

RUN chmod +x /vantage6/configs/server.sh

# expose the proxy server port
ARG port=80
EXPOSE ${port} 2222
ENV PROXY_SERVER_PORT ${port}
