#!/usr/bin/env bash
set -euo pipefail
CONF="${1:-config/nftables.conf}"

echo "[*] Applying nftables rules from $CONF"
sudo nft -f "$CONF"
sudo nft list ruleset
