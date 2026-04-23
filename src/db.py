import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mac_address TEXT UNIQUE NOT NULL,
    ip_address TEXT,
    hostname TEXT,
    vendor TEXT,
    device_name TEXT,
    model TEXT,
    version TEXT,
    description TEXT,
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
    packet_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running'
);
CREATE TABLE IF NOT EXISTS whitelist_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_mac TEXT,
    allowed_dest TEXT,
    allowed_port INTEGER,
    protocol TEXT,
    description TEXT,
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
CREATE TABLE IF NOT EXISTS data_rate_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_mac TEXT NOT NULL,
    bytes_per_sec INTEGER NOT NULL,
    packets_per_sec INTEGER NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def get_connection(db_path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    # add columns that didn't exist in the first version of the schema
    for col in ["device_name TEXT", "model TEXT", "version TEXT", "description TEXT"]:
        try:
            conn.execute(f"ALTER TABLE devices ADD COLUMN {col}")
        except Exception:
            pass
    try:
        conn.execute("ALTER TABLE captures ADD COLUMN status TEXT DEFAULT 'running'")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE whitelist_rules ADD COLUMN description TEXT")
    except Exception:
        pass
    conn.commit()


def upsert_device(conn, mac_address, ip_address, hostname, vendor, first_seen, last_seen, status="online"):
    row = conn.execute("SELECT id FROM devices WHERE mac_address=?", (mac_address,)).fetchone()
    if row:
        conn.execute(
            "UPDATE devices SET ip_address=?, hostname=?, vendor=?, last_seen=?, status=? WHERE mac_address=?",
            (ip_address, hostname, vendor, last_seen, status, mac_address)
        )
    else:
        conn.execute(
            "INSERT INTO devices (mac_address, ip_address, hostname, vendor, first_seen, last_seen, status) VALUES (?,?,?,?,?,?,?)",
            (mac_address, ip_address, hostname, vendor, first_seen, last_seen, status)
        )
    conn.commit()


def update_device_info(conn, device_id, device_name, model, version, description, notes):
    conn.execute(
        "UPDATE devices SET device_name=?, model=?, version=?, description=?, notes=? WHERE id=?",
        (device_name, model, version, description, notes, device_id)
    )
    conn.commit()


def fetch_devices(conn):
    return conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()


def fetch_device_by_id(conn, device_id):
    return conn.execute("SELECT * FROM devices WHERE id=?", (device_id,)).fetchone()


def add_capture(conn, device_mac, pcap_path, start_time, end_time=None, packet_count=0):
    cur = conn.execute(
        "INSERT INTO captures (device_mac, pcap_path, start_time, end_time, packet_count, status) VALUES (?,?,?,?,?,'running')",
        (device_mac, pcap_path, start_time, end_time, packet_count)
    )
    conn.commit()
    return cur.lastrowid


def update_capture_end(conn, capture_id, end_time, packet_count=0):
    conn.execute(
        "UPDATE captures SET end_time=?, packet_count=?, status='done' WHERE id=?",
        (end_time, packet_count, capture_id)
    )
    conn.commit()


def fetch_captures(conn):
    return conn.execute("SELECT * FROM captures ORDER BY id DESC").fetchall()


def delete_capture(conn, capture_id):
    row = conn.execute("SELECT pcap_path FROM captures WHERE id=?", (capture_id,)).fetchone()
    if row:
        conn.execute("DELETE FROM captures WHERE id=?", (capture_id,))
        conn.commit()
        return row["pcap_path"]
    return None


def add_whitelist_rule(conn, device_mac, allowed_dest, allowed_port, protocol, description=None, enabled=1):
    cur = conn.execute(
        "INSERT INTO whitelist_rules (device_mac, allowed_dest, allowed_port, protocol, description, enabled) VALUES (?,?,?,?,?,?)",
        (device_mac, allowed_dest, allowed_port, protocol, description, enabled)
    )
    conn.commit()
    return cur.lastrowid


def delete_whitelist_rule(conn, rule_id):
    conn.execute("DELETE FROM whitelist_rules WHERE id=?", (rule_id,))
    conn.commit()


def fetch_whitelist_rules(conn):
    return conn.execute("SELECT * FROM whitelist_rules ORDER BY id DESC").fetchall()


def add_alert(conn, device_mac, alert_type, severity, message, created_at):
    cur = conn.execute(
        "INSERT INTO alerts (device_mac, alert_type, severity, message, created_at) VALUES (?,?,?,?,?)",
        (device_mac, alert_type, severity, message, created_at)
    )
    conn.commit()
    return cur.lastrowid


def fetch_alerts(conn):
    return conn.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()


def add_rate_event(conn, device_mac, bytes_per_sec, packets_per_sec, action_taken, timestamp):
    cur = conn.execute(
        "INSERT INTO rate_events (device_mac, bytes_per_sec, packets_per_sec, action_taken, timestamp) VALUES (?,?,?,?,?)",
        (device_mac, bytes_per_sec, packets_per_sec, action_taken, timestamp)
    )
    conn.commit()
    return cur.lastrowid


def fetch_rate_events(conn):
    return conn.execute("SELECT * FROM rate_events ORDER BY id DESC").fetchall()


def add_data_rate_history(conn, device_mac, bytes_per_sec, packets_per_sec):
    conn.execute(
        "INSERT INTO data_rate_history (device_mac, bytes_per_sec, packets_per_sec, recorded_at) VALUES (?,?,?,?)",
        (device_mac, bytes_per_sec, packets_per_sec, datetime.utcnow().isoformat())
    )
    conn.commit()


def fetch_data_rate_history(conn, device_mac, days=7):
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    return conn.execute(
        "SELECT * FROM data_rate_history WHERE device_mac=? AND recorded_at>=? ORDER BY recorded_at ASC",
        (device_mac, since)
    ).fetchall()


def fetch_all_rate_history(conn, days=7):
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    return conn.execute(
        "SELECT * FROM data_rate_history WHERE recorded_at>=? ORDER BY recorded_at ASC",
        (since,)
    ).fetchall()


def add_system_log(conn, level, message):
    conn.execute(
        "INSERT INTO system_logs (level, message, created_at) VALUES (?,?,?)",
        (level, message, datetime.utcnow().isoformat())
    )
    conn.commit()


def fetch_system_logs(conn):
    return conn.execute("SELECT * FROM system_logs ORDER BY id DESC LIMIT 200").fetchall()


def delete_system_logs(conn):
    conn.execute("DELETE FROM system_logs")
    conn.commit()


def cleanup_old_records(conn, history_days):
    cutoff = (datetime.utcnow() - timedelta(days=history_days)).isoformat()
    r1 = conn.execute("DELETE FROM rate_events WHERE timestamp < ?", (cutoff,)).rowcount
    r2 = conn.execute("DELETE FROM data_rate_history WHERE recorded_at < ?", (cutoff,)).rowcount
    r3 = conn.execute("DELETE FROM system_logs WHERE created_at < ?", (cutoff,)).rowcount
    conn.commit()
    return {"rate_events": r1, "history": r2, "logs": r3}