FROM large-data-test-algorithm-base:latest
ARG PKG_NAME="dhd-test-algorithm"

COPY . /app
RUN pip install /app
ENV PKG_NAME=${PKG_NAME}

CMD python -c "from vantage6.algorithm.tools.wrap import wrap_algorithm; wrap_algorithm()"
