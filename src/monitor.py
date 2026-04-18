from __future__ import annotations

import subprocess
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, Tuple

from scapy.all import sniff  # type: ignore

from .alerts import create_alert
from .db import add_rate_event, fetch_devices


class TrafficMonitor:
    def __init__(
        self,
        conn,
        interface: str,
        bytes_threshold: int,
        packets_threshold: int,
        throttle_rate: str,
        throttle_duration_seconds: int,
    ) -> None:
        self.conn = conn
        self.interface = interface
        self.bytes_threshold = bytes_threshold
        self.packets_threshold = packets_threshold
        self.throttle_rate = throttle_rate
        self.throttle_duration_seconds = throttle_duration_seconds

    def sample(self, timeout_seconds: int = 5) -> Dict[str, Tuple[int, int]]:
        stats: Dict[str, list[int]] = defaultdict(lambda: [0, 0])

        def handle(packet):
            if not hasattr(packet, "src"):
                return
            mac = getattr(packet, "src", None)
            if not mac:
                return
            stats[mac][0] += len(bytes(packet))
            stats[mac][1] += 1

        sniff(iface=self.interface, prn=handle, store=False, timeout=timeout_seconds)
        return {mac: (values[0] // max(timeout_seconds, 1), values[1] // max(timeout_seconds, 1)) for mac, values in stats.items()}

    def throttle_interface(self) -> None:
        subprocess.run(
            ["sudo", "tc", "qdisc", "replace", "dev", self.interface, "root", "tbf", "rate", self.throttle_rate, "burst", "32kbit", "latency", "400ms"],
            check=False,
        )

        def clear_later():
            time.sleep(self.throttle_duration_seconds)
            subprocess.run(["sudo", "tc", "qdisc", "del", "dev", self.interface, "root"], check=False)

        threading.Thread(target=clear_later, daemon=True).start()

    def evaluate(self) -> None:
        measurements = self.sample()
        for mac, (bytes_per_sec, packets_per_sec) in measurements.items():
            if bytes_per_sec > self.bytes_threshold or packets_per_sec > self.packets_threshold:
                message = (
                    f"Device {mac} exceeded traffic threshold: "
                    f"{bytes_per_sec} B/s, {packets_per_sec} pkt/s"
                )
                create_alert(self.conn, mac, "rate_threshold_exceeded", "high", message)
                self.throttle_interface()
                add_rate_event(
                    self.conn,
                    device_mac=mac,
                    bytes_per_sec=bytes_per_sec,
                    packets_per_sec=packets_per_sec,
                    action_taken=f"throttle {self.interface} to {self.throttle_rate}",
                    timestamp=datetime.utcnow().isoformat(),
                )
