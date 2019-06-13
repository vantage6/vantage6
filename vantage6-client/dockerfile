# poc that we can dockerize the node-instance
FROM python:3

# copy all files to app folder
COPY . /app

# install the app
RUN pip install /app

# mount the config file
CMD jnode start --config /input/config.yaml
