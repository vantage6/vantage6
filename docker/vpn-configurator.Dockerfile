FROM ubuntu:22.04

RUN apt update
RUN apt install iproute2 iptables -y