# poc that we can dockerize the node-instance
FROM ppdli-base

LABEL version="0.0.1"
LABEL infrastructure_version = "0.3.0"
LABEL maintainer="Frank Martin <f.martin@iknl.nl>"

COPY . /vantage
RUN pip install /vantage

# copy start file to app folder
COPY /vantage/node/start.py /app/start.py

# expose the proxy server port
ARG port=80
EXPOSE ${port}
ENV PROXY_SERVER_PORT ${port}

# create entrypoint
ENTRYPOINT [ "python", "/app/start.py"]