FROM debian:12

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y squid \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /app

COPY services/squid/ /app/
RUN chmod +x /app/entry.sh

ENTRYPOINT ["/app/entry.sh"]
