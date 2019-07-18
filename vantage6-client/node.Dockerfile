# poc that we can dockerize the node-instance
FROM ppdli-base

# copy all files to app folder
COPY "/joey/node" "/app"

# expose the proxy server port
ARG port=80
EXPOSE ${port}
ENV PROXY_SERVER_PORT ${port}

# create entrypoint
ENTRYPOINT [ "python", "/app/start.py"]