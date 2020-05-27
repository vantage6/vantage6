# poc that we can dockerize the node-instance
FROM ppdli-base

LABEL version="0.0.1"
LABEL infrastructure_version = "1.0.0"
LABEL maintainer="Frank Martin <f.martin@iknl.nl>"

RUN pip install git+https://github.com/IKNL/vantage6
RUN pip install git+https://github.com/IKNL/vantage6-common
RUN pip install git+https://github.com/IKNL/vantage6-client

COPY . /vantage6
RUN pip install -e /vantage6

# copy start file to app folder
COPY /vantage6/node/start.py /app/start.py

# expose the proxy server port
ARG port=80
EXPOSE ${port}
ENV PROXY_SERVER_PORT ${port}

# create entrypoint
CMD [ "python", "/app/start.py"]