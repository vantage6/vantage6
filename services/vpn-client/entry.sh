#!/bin/sh

echo "entrypoint.sh"

ISOLATED_SUBNET=$(ip -f inet addr show eth1| sed -En -e 's/.*inet ([0-9./]+).*/\1/p')

# Forward all traffic via VPN
iptables -F FORWARD
iptables -P FORWARD DROP
iptables -A FORWARD -i eth1 -o tun0 -j ACCEPT
iptables -A FORWARD -o eth1 -i tun0 -j ACCEPT
iptables -A FORWARD -i eth1 -o eth1 -j ACCEPT

# for all outgoing VPN traffic, pretend that it comes from the VPN client (even
# if it is just forwarded)
iptables -t nat -A POSTROUTING -o tun0 -j MASQUERADE
iptables -t nat -A POSTROUTING -o eth1 -s ISOLATED_SUBNET -d ISOLATED_SUBNET -j MASQUERADE
# Run vpn
echo "Starting vpn client..."
openvpn --config "$VPN_CONFIG" \
    --connect-retry-max 1 \
    --pull-filter ignore "route-ipv6" \
    --pull-filter ignore "ifconfig-ipv6" \
    --script-security 2 \
    --up-restart \
    --ping-exit 10 \
    --cd /mnt/vpn &
openvpn_child=$!

wait $openvpn_child
echo "Exiting, status $openvpn_child"