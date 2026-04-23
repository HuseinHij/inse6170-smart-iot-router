import smtplib
import subprocess
import threading
import time
from collections import defaultdict
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from scapy.all import sniff

from .db import add_alert, add_rate_event, add_data_rate_history


class TrafficMonitor:
    def __init__(self, conn, interface, bytes_threshold, packets_threshold,
                 throttle_rate, throttle_duration_seconds,
                 ips_capture_seconds=10, captures_dir="captures",
                 tcpdump_bin="/usr/bin/tcpdump", notify_config=None):
        self.conn = conn
        self.interface = interface
        self.bytes_threshold = bytes_threshold
        self.packets_threshold = packets_threshold
        self.throttle_rate = throttle_rate
        self.throttle_duration_seconds = throttle_duration_seconds
        self.ips_capture_seconds = ips_capture_seconds
        self.captures_dir = Path(captures_dir)
        self.tcpdump_bin = tcpdump_bin
        self.notify_config = notify_config or {}

    def sample(self, timeout=5):
        stats = defaultdict(lambda: [0, 0])

        def handle(pkt):
            mac = getattr(pkt, "src", None)
            if mac:
                stats[mac][0] += len(bytes(pkt))
                stats[mac][1] += 1

        sniff(iface=self.interface, prn=handle, store=False, timeout=timeout)
        return {mac: (v[0] // timeout, v[1] // timeout) for mac, v in stats.items()}

    def _ips_capture(self, mac):
        # run a short dedicated capture when anomaly is detected (10 seconds)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = self.captures_dir / f"ips_{mac.replace(':', '')}_{ts}.pcap"
        subprocess.run(
            [self.tcpdump_bin, "-i", self.interface, "-w", str(path), "-G",
             str(self.ips_capture_seconds), "-W", "1"],
            timeout=self.ips_capture_seconds + 5,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def _send_email(self, mac, bps, pps):
        cfg = self.notify_config
        if not cfg.get("enabled"):
            return
        try:
            body = f"IPS Alert\nDevice: {mac}\nTraffic: {bps} B/s, {pps} pkt/s\nAction: throttled to {self.throttle_rate}\nTime: {datetime.utcnow().isoformat()}"
            msg = MIMEText(body)
            msg["Subject"] = f"[IoT Router] Alert - {mac}"
            msg["From"] = cfg["smtp_user"]
            msg["To"] = cfg["recipient"]
            with smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"])) as s:
                s.starttls()
                s.login(cfg["smtp_user"], cfg["smtp_password"])
                s.send_message(msg)
        except Exception as e:
            print(f"[email] failed: {e}")

    def throttle(self):
        subprocess.run(
            ["sudo", "tc", "qdisc", "replace", "dev", self.interface,
             "root", "tbf", "rate", self.throttle_rate, "burst", "32kbit", "latency", "400ms"],
            check=False
        )
        def clear():
            time.sleep(self.throttle_duration_seconds)
            subprocess.run(["sudo", "tc", "qdisc", "del", "dev", self.interface, "root"], check=False)
        threading.Thread(target=clear, daemon=True).start()

    def evaluate(self):
        for mac, (bps, pps) in self.sample().items():
            add_data_rate_history(self.conn, mac, bps, pps)
            if bps > self.bytes_threshold or pps > self.packets_threshold:
                msg = f"Device {mac} exceeded threshold: {bps} B/s, {pps} pkt/s"
                add_alert(self.conn, mac, "rate_threshold_exceeded", "high", msg, datetime.utcnow().isoformat())
                self.throttle()
                add_rate_event(self.conn, mac, bps, pps,
                               f"throttle {self.interface} to {self.throttle_rate}",
                               datetime.utcnow().isoformat())
                threading.Thread(target=self._ips_capture, args=(mac,), daemon=True).start()
                threading.Thread(target=self._send_email, args=(mac, bps, pps), daemon=True).start()