from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .db import add_capture, update_capture_end


@dataclass
class CaptureSession:
    capture_id: int
    process: subprocess.Popen
    pcap_path: str
    start_time: str


class PacketCaptureManager:
    def __init__(self, conn, captures_dir: str, tcpdump_bin: str = "/usr/bin/tcpdump") -> None:
        self.conn = conn
        self.captures_dir = Path(captures_dir)
        self.captures_dir.mkdir(parents=True, exist_ok=True)
        self.tcpdump_bin = tcpdump_bin
        self.current: Optional[CaptureSession] = None

    def start(self, interface: str, name_prefix: str = "capture") -> Optional[CaptureSession]:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        pcap_path = self.captures_dir / f"{name_prefix}_{timestamp}.pcap"
        start_time = datetime.utcnow().isoformat()

        cmd = [
            self.tcpdump_bin,
            "-i", interface,
            "-w", str(pcap_path),
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        capture_id = add_capture(
            conn=self.conn,
            device_mac=None,
            pcap_path=str(pcap_path),
            start_time=start_time,
        )
        session = CaptureSession(
            capture_id=capture_id,
            process=process,
            pcap_path=str(pcap_path),
            start_time=start_time,
        )
        self.current = session
        return session

    @staticmethod
    def _count_packets(pcap_path: str, tcpdump_bin: str) -> int:
        """Count packets in a PCAP file by reading it back with tcpdump."""
        try:
            result = subprocess.run(
                [tcpdump_bin, "-r", pcap_path, "-nn", "--count"],
                capture_output=True,
                text=True,
                check=False,
            )
            # tcpdump --count outputs "<N> packets" to stderr
            for line in (result.stderr + result.stdout).splitlines():
                parts = line.strip().split()
                if parts and parts[0].isdigit():
                    return int(parts[0])
        except Exception:
            pass
        return 0

    def stop(self) -> None:
        if not self.current:
            return
        session = self.current
        if session.process.poll() is None:
            session.process.send_signal(signal.SIGINT)
            try:
                session.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                session.process.kill()
        end_time = datetime.utcnow().isoformat()
        packet_count = self._count_packets(session.pcap_path, self.tcpdump_bin)
        update_capture_end(self.conn, session.capture_id, end_time=end_time, packet_count=packet_count)
        self.current = None