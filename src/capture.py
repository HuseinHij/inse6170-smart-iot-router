import signal
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from .db import add_capture, update_capture_end


class PacketCaptureManager:
    def __init__(self, conn, captures_dir, tcpdump_bin="/usr/bin/tcpdump"):
        self.conn = conn
        self.captures_dir = Path(captures_dir)
        self.captures_dir.mkdir(parents=True, exist_ok=True)
        self.tcpdump_bin = tcpdump_bin
        # active sessions keyed by capture_id
        self.active = {}

    def start_capture(self, interface, filename, device_mac=None, duration=None, packet_count=None):
        # build pcap path — use admin-supplied filename
        safe = filename.strip().replace(" ", "_") or "capture"
        if not safe.endswith(".pcap"):
            safe += ".pcap"
        pcap_path = self.captures_dir / safe
        start_time = datetime.utcnow().isoformat()

        cmd = [self.tcpdump_bin, "-i", interface, "-w", str(pcap_path)]
        if device_mac:
            cmd += ["ether", "host", device_mac]
        if packet_count:
            cmd += ["-c", str(packet_count)]

        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        capture_id = add_capture(self.conn, device_mac, str(pcap_path), start_time)
        self.active[capture_id] = process

        # if duration given, stop automatically after N seconds
        if duration:
            def auto_stop():
                try:
                    process.wait(timeout=int(duration))
                except subprocess.TimeoutExpired:
                    process.send_signal(signal.SIGINT)
                    process.wait()
                self._finish(capture_id)
            threading.Thread(target=auto_stop, daemon=True).start()

        return capture_id

    def stop_capture(self, capture_id):
        proc = self.active.get(capture_id)
        if proc and proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            proc.wait()
        self._finish(capture_id)

    def _finish(self, capture_id):
        self.active.pop(capture_id, None)
        update_capture_end(self.conn, capture_id, datetime.utcnow().isoformat(), 0)