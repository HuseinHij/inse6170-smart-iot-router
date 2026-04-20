#!/usr/bin/env bash
set -euo pipefail

AP_IFACE="${1:-wlan0}"
AP_IP="${2:-192.168.50.1/24}"
HOSTAPD_CONF="${3:-config/hostapd.conf}"

echo "[*] Bringing up hotspot interface: $AP_IFACE"
sudo ip link set "$AP_IFACE" down || true
sudo ip addr flush dev "$AP_IFACE" || true
sudo ip addr add "$AP_IP" dev "$AP_IFACE"
sudo ip link set "$AP_IFACE" up

echo "[*] Starting hostapd"
sudo hostapd "$HOSTAPD_CONF"
