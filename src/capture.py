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
        self.active = {}

    def start_capture(self, interface, filename, device_mac=None, duration=None, packet_count=None):
        safe = filename.strip().replace(" ", "_") or "capture"
        if not safe.endswith(".pcap"):
            safe += ".pcap"
        pcap_path = self.captures_dir / safe
        start_time = datetime.utcnow().isoformat()

        cmd = [self.tcpdump_bin, "-i", interface]
        if packet_count:
            cmd += ["-c", str(packet_count)]
        cmd += ["-w", str(pcap_path)]
        if device_mac:
            cmd += ["ether", "host", device_mac]

        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        capture_id = add_capture(self.conn, device_mac, str(pcap_path), start_time)
        self.active[capture_id] = process


        def watch_capture():
            try:
                if duration:
                    process.wait(timeout=int(duration))
                else:
                    process.wait()
            except subprocess.TimeoutExpired:
                process.send_signal(signal.SIGINT)
                process.wait()
            finally:
                if capture_id in self.active:
                    self._finish(capture_id, pcap_path)

        threading.Thread(target=watch_capture, daemon=True).start()

        return capture_id

    def stop_capture(self, capture_id):
        proc = self.active.get(capture_id)
        if proc and proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            proc.wait()

        pcap_path = None
        row = self.conn.execute(
            "SELECT file_path FROM captures WHERE id = ?",
            (capture_id,),
        ).fetchone()
        if row:
            pcap_path = row["file_path"] if hasattr(row, "keys") else row[0]

        self._finish(capture_id, pcap_path)

    def _finish(self, capture_id, pcap_path=None):
        self.active.pop(capture_id, None)

        packets = 0
        if pcap_path and Path(pcap_path).exists():
            result = subprocess.run(
                [self.tcpdump_bin, "-nn", "-r", str(pcap_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            packets = len([line for line in result.stdout.splitlines() if line.strip()])

        update_capture_end(self.conn, capture_id, datetime.utcnow().isoformat(), packets)