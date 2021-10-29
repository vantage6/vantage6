FROM alpine:3.13

RUN apk add --no-cache \
        bind-tools \
        openvpn

RUN mkdir /app

COPY . /app/

ENTRYPOINT ["/app/entry.sh"]