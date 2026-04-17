from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional, Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mac_address TEXT UNIQUE NOT NULL,
    ip_address TEXT,
    hostname TEXT,
    vendor TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    status TEXT DEFAULT 'online',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_mac TEXT,
    pcap_path TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    packet_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS whitelist_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_mac TEXT,
    allowed_dest TEXT,
    allowed_port INTEGER,
    protocol TEXT,
    enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_mac TEXT,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rate_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_mac TEXT,
    bytes_per_sec INTEGER,
    packets_per_sec INTEGER,
    action_taken TEXT,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_device(
    conn: sqlite3.Connection,
    mac_address: str,
    ip_address: Optional[str],
    hostname: Optional[str],
    vendor: Optional[str],
    first_seen: str,
    last_seen: str,
    status: str = "online",
) -> None:
    existing = conn.execute(
        "SELECT id, first_seen FROM devices WHERE mac_address = ?",
        (mac_address,),
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE devices
            SET ip_address = ?, hostname = ?, vendor = ?, last_seen = ?, status = ?
            WHERE mac_address = ?
            """,
            (ip_address, hostname, vendor, last_seen, status, mac_address),
        )
    else:
        conn.execute(
            """
            INSERT INTO devices (mac_address, ip_address, hostname, vendor, first_seen, last_seen, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (mac_address, ip_address, hostname, vendor, first_seen, last_seen, status),
        )
    conn.commit()


def fetch_devices(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM devices ORDER BY last_seen DESC, mac_address ASC"
    ).fetchall()


def add_capture(
    conn: sqlite3.Connection,
    device_mac: Optional[str],
    pcap_path: str,
    start_time: str,
    end_time: Optional[str] = None,
    packet_count: int = 0,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO captures (device_mac, pcap_path, start_time, end_time, packet_count)
        VALUES (?, ?, ?, ?, ?)
        """,
        (device_mac, pcap_path, start_time, end_time, packet_count),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_capture_end(
    conn: sqlite3.Connection,
    capture_id: int,
    end_time: str,
    packet_count: int = 0,
) -> None:
    conn.execute(
        "UPDATE captures SET end_time = ?, packet_count = ? WHERE id = ?",
        (end_time, packet_count, capture_id),
    )
    conn.commit()


def fetch_captures(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM captures ORDER BY id DESC").fetchall()


def add_alert(
    conn: sqlite3.Connection,
    device_mac: Optional[str],
    alert_type: str,
    severity: str,
    message: str,
    created_at: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO alerts (device_mac, alert_type, severity, message, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (device_mac, alert_type, severity, message, created_at),
    )
    conn.commit()
    return int(cur.lastrowid)


def fetch_alerts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()


def add_whitelist_rule(
    conn: sqlite3.Connection,
    device_mac: Optional[str],
    allowed_dest: Optional[str],
    allowed_port: Optional[int],
    protocol: Optional[str],
    enabled: int = 1,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO whitelist_rules (device_mac, allowed_dest, allowed_port, protocol, enabled)
        VALUES (?, ?, ?, ?, ?)
        """,
        (device_mac, allowed_dest, allowed_port, protocol, enabled),
    )
    conn.commit()
    return int(cur.lastrowid)


def fetch_whitelist_rules(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM whitelist_rules ORDER BY id DESC").fetchall()


def add_rate_event(
    conn: sqlite3.Connection,
    device_mac: Optional[str],
    bytes_per_sec: int,
    packets_per_sec: int,
    action_taken: str,
    timestamp: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO rate_events (device_mac, bytes_per_sec, packets_per_sec, action_taken, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        (device_mac, bytes_per_sec, packets_per_sec, action_taken, timestamp),
    )
    conn.commit()
    return int(cur.lastrowid)
