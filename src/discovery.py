from __future__ import annotations

import socket
import subprocess
from datetime import datetime
from typing import Any

from .db import upsert_device
from .oui_lookup import OUILookup


def parse_ip_neigh(output: str) -> list[dict[str, str]]:
    devices: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        ip_address = parts[0]
        try:
            lladdr_index = parts.index("lladdr")
        except ValueError:
            continue
        mac_address = parts[lladdr_index + 1]
        state = parts[-1]
        devices.append(
            {
                "ip_address": ip_address,
                "mac_address": mac_address,
                "state": state,
            }
        )
    return devices


def safe_hostname(ip_address: str) -> str | None:
    try:
        return socket.gethostbyaddr(ip_address)[0]
    except Exception:
        return None


def discover_devices(interface: str) -> list[dict[str, str]]:
    result = subprocess.run(
        ["ip", "neigh", "show", "dev", interface],
        capture_output=True,
        text=True,
        check=False,
    )
    return parse_ip_neigh(result.stdout)


def sync_inventory(conn: Any, interface: str, oui_lookup: OUILookup) -> list[dict[str, str]]:
    now = datetime.utcnow().isoformat()
    discovered = discover_devices(interface)
    for item in discovered:
        vendor = oui_lookup.lookup(item["mac_address"])
        hostname = safe_hostname(item["ip_address"])
        upsert_device(
            conn=conn,
            mac_address=item["mac_address"],
            ip_address=item["ip_address"],
            hostname=hostname,
            vendor=vendor,
            first_seen=now,
            last_seen=now,
            status="online",
        )
    return discovered
