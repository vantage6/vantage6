FROM python:3.10-slim-bullseye

LABEL version=${TAG}
LABEL maintainer="F.C. Martin <f.martin@iknl.nl>"

# we need to copy the readme for the setup.py from the vantage6-algorithm-tools
# as it uses the top-level readme.
COPY ./README.md /README.md
COPY ./vantage6-common /vantage6-common
COPY ./vantage6-algorithm-tools /vantage6-algorithm-tools

RUN pip install /vantage6-common
RUN pip install /vantage6-algorithm-tools