FROM ubuntu:22.04

RUN apt-get update \
    && apt-get install -y iproute2 iptables \
    && rm -rf /var/lib/apt/lists/*