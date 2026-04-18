from __future__ import annotations

import subprocess

from .db import fetch_whitelist_rules


def run_nft_script(commands: list[str]) -> None:
    script = "\n".join(commands) + "\n"
    subprocess.run(
        ["sudo", "nft", "-f", "-"],
        input=script,
        text=True,
        check=True,
    )


def apply_base_policy() -> None:
    subprocess.run(["sudo", "nft", "delete", "table", "inet", "iot_filter"], check=False)

    commands = [
        "add table inet iot_filter",
        "add chain inet iot_filter forward { type filter hook forward priority 0; policy accept; }",
    ]
    run_nft_script(commands)


def rebuild_whitelist(conn) -> None:
    rules = fetch_whitelist_rules(conn)

    subprocess.run(["sudo", "nft", "delete", "table", "inet", "iot_filter"], check=False)

    commands = [
        "add table inet iot_filter",
        "add chain inet iot_filter forward { type filter hook forward priority 0; policy drop; }",
    ]

    for rule in rules:
        if not rule["enabled"]:
            continue

        protocol = (rule["protocol"] or "tcp").lower()
        dest = rule["allowed_dest"] or "0.0.0.0/0"
        port = rule["allowed_port"]
        device_mac = rule["device_mac"]

        if port is not None and device_mac:
            commands.append(
                f"add rule inet iot_filter forward ether saddr {device_mac} ip daddr {dest} {protocol} dport {port} accept"
            )
        elif device_mac:
            commands.append(
                f"add rule inet iot_filter forward ether saddr {device_mac} ip daddr {dest} accept"
            )
        else:
            commands.append(
                f"add rule inet iot_filter forward ip daddr {dest} accept"
            )

    run_nft_script(commands)