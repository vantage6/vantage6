# HTTP(S) proxy that Docker nodes start for algorithm steps with a whitelist. The
# node copies the configuration to /etc/squid/squid.conf before starting it.
ARG ALPINE_VERSION=3
FROM alpine:${ALPINE_VERSION}

RUN apk add --no-cache squid

USER squid
EXPOSE 3128
ENTRYPOINT ["squid", "-N", "-f", "/etc/squid/squid.conf"]
