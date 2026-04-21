FROM debian:12

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y openssh-server curl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /app

COPY services/ssh-tunnel/ /app/
RUN chmod +x /app/entry.sh

ENTRYPOINT ["/app/entry.sh"]