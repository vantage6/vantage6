FROM debian:12

RUN apt update
RUN apt upgrade -y

RUN apt install -y openssh-server
RUN apt install -y curl

RUN mkdir /app

COPY services/ssh-tunnel/ /app/
RUN chmod +x /app/entry.sh

ENTRYPOINT ["/app/entry.sh"]