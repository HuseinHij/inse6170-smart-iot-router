#!/usr/bin/env bash
set -euo pipefail
IFACE="${1:-wlan0}"

echo "[*] Removing traffic control rules on $IFACE"
sudo tc qdisc del dev "$IFACE" root || true
