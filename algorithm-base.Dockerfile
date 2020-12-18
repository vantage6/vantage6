FROM python:3.7-slim-buster

RUN pip install vantage6-client

# Tell docker to execute `docker_wrapper()` when the image is run.
# CMD python -c "from vantage6.tools.docker_wrapper import docker_wrapper; docker_wrapper('${PKG_NAME}')"