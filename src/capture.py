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
            "-i",
            interface,
            "-w",
            str(pcap_path),
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

    def stop(self) -> None:
        if not self.current:
            return
        session = self.current
        if session.process.poll() is None:
            session.process.send_signal(signal.SIGINT)
            session.process.wait(timeout=10)
        end_time = datetime.utcnow().isoformat()
        packet_count = 0
        update_capture_end(self.conn, session.capture_id, end_time=end_time, packet_count=packet_count)
        self.current = None
