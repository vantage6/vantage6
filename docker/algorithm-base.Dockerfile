FROM python:3.7-slim-buster

# we need to copy the readme for the setup.py from the vantage6-client
# as it uses the top-level readme.
COPY ./README.md /README.md
COPY ./vantage6-client /vantage6-client

RUN pip install /vantage6-client

# Tell docker to execute `docker_wrapper()` when the image is run.
# CMD python -c "from vantage6.tools.docker_wrapper import docker_wrapper; docker_wrapper('${PKG_NAME}')"