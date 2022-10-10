ARG ALPINE_VERSION=3.13
FROM alpine:${ALPINE_VERSION}

RUN apk add --no-cache \
        bind-tools \
        openvpn

RUN mkdir /app

COPY vpn/vpn-client/ /app/

ENTRYPOINT ["/app/entry.sh"]
