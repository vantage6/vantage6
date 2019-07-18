# poc that we can dockerize the node-instance
FROM ppdli-base

# copy all files to app folder
COPY "/joey/node" "/app"

# expose the proxy server port
EXPOSE 80

# create entrypoint
ENTRYPOINT [ "python", "/app/start.py"]
