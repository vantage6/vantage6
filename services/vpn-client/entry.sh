#!/bin/sh

echo "entrypoint.sh"

# Forward all traffic via VPN
iptables -F FORWARD
iptables -P FORWARD DROP
iptables -A FORWARD -i eth1 -o tun0 -j ACCEPT
iptables -A FORWARD -o eth1 -i tun0 -j ACCEPT
iptables -A FORWARD -i eth1 -o eth1 -j ACCEPT

# for all outgoing VPN traffic, pretend that it comes from the VPN client (even
# if it is just forwarded)
iptables -t nat -A POSTROUTING -o tun0 -j MASQUERADE

# Check isolated network interface. Wait until it is up.
isolated_subnet=""
while [ "$isolated_subnet" = "" ];do
  eth1_interface=$(ip addr show eth1)
  echo "eth1 interface: " "$eth1_interface"

  # Extract ip range from string
  isolated_subnet=$(echo "$eth1_interface" | sed -En -e 's/.*inet ([0-9./]+).*/\1/p')
  echo "Isolated subnet is " "$isolated_subnet"
done


iptables -t nat -A POSTROUTING -o eth1 -s "$isolated_subnet" -d "$isolated_subnet" -j MASQUERADE
# Run vpn
echo "Starting vpn client..."
openvpn --config "$VPN_CONFIG" \
    --connect-retry-max 1 \
    --pull-filter ignore "route-ipv6" \
    --pull-filter ignore "ifconfig-ipv6" \
    --script-security 2 \
    --up-restart \
    --ping-exit 30 \
    --cd /mnt/vpn &
openvpn_child=$!

wait $openvpn_child
echo "Exiting, status $openvpn_child"