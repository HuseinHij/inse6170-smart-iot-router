#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_IFACE="${1:-eth0}"
AP_IFACE="${2:-wlan0}"
AP_SUBNET="${3:-192.168.50.0/24}"

echo "[*] Enabling IPv4 forwarding"
sudo sysctl -w net.ipv4.ip_forward=1

echo "[*] Applying nftables NAT rules"
sudo nft 'add table ip nat' || true
sudo nft 'add chain ip nat postrouting { type nat hook postrouting priority 100; }' || true
sudo nft add rule ip nat postrouting oifname "$UPSTREAM_IFACE" ip saddr "$AP_SUBNET" masquerade || true

echo "[*] Allowing forwarding"
sudo nft add table inet filter || true
sudo nft 'add chain inet filter forward { type filter hook forward priority 0; policy accept; }' || true
sudo nft add rule inet filter forward iifname "$AP_IFACE" oifname "$UPSTREAM_IFACE" accept || true
sudo nft add rule inet filter forward iifname "$UPSTREAM_IFACE" oifname "$AP_IFACE" ct state related,established accept || true
