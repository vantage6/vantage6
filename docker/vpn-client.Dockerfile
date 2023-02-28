ARG ALPINE_VERSION=3
FROM alpine:${ALPINE_VERSION}

RUN apk add --no-cache \
        bind-tools \
        openvpn \
        iptables

RUN mkdir /app

COPY services/vpn-client/ /app/
RUN chmod +x /app/entry.sh

ENTRYPOINT ["/app/entry.sh"]
