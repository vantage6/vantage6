FROM debian:10

RUN apt-get update
RUN apt-get upgrade -y

RUN apt-get install -y squid3

RUN mkdir /app

COPY services/squid/ /app/
RUN chmod +x /app/entry.sh

ENTRYPOINT ["/app/entry.sh"]
