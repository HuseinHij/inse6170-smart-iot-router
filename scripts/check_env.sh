#!/usr/bin/env bash
set -euo pipefail

echo "[*] Checking Python"
python3 --version

echo "[*] Checking required Linux tools"
for cmd in hostapd nft tc tcpdump sqlite3 ip sysctl; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "  - found $cmd"
  else
    echo "  - missing $cmd"
  fi
done

echo "[*] Checking wireless interfaces"
ip link show
