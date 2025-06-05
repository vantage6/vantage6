FROM python:3.10-slim-bullseye

LABEL version=${TAG}
LABEL maintainer="F.C. Martin <f.martin@iknl.nl>"

# we need to copy the readme for the setup.py from the vantage6-algorithm-tools
# as it uses the top-level readme.
COPY ./README.md /README.md
COPY ./vantage6-common /vantage6-common
COPY ./vantage6-algorithm-tools /vantage6-algorithm-tools
COPY ./vantage6-client /vantage6-client
COPY ./vantage6 /vantage6

RUN pip install --upgrade pip
# Install requirements. We cannot rely on setup.py because of the way
# python resolves package versions. To control all dependencies we install
# them from the requirements.txt
# This is also done in the base-image to safe build time. We redo it here
# to allow for dependency upgrades in minor and patch versions.
RUN pip install -r /vantage6/requirements.txt \
  --extra-index-url https://www.piwheels.org/simple
RUN pip install /vantage6-common
RUN pip install /vantage6-algorithm-tools
RUN pip install /vantage6-client