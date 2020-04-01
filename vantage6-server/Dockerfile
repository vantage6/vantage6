# poc that we can dockerize the node-instance
FROM harbor.distributedlearning.ai/infrastructure/base

LABEL version="0.0.1"
LABEL infrastructure_version = "1.0.0"
LABEL maintainer="Frank Martin <f.martin@iknl.nl>"

RUN pip install git+https://github.com/IKNL/vantage6
RUN pip install git+https://github.com/IKNL/vantage6-common
RUN pip install git+https://github.com/IKNL/vantage6-client

COPY . /vantage6
RUN pip install /vantage6
