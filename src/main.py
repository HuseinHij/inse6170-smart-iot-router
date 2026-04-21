from __future__ import annotations

import atexit
import os
from datetime import datetime
from pathlib import Path

from .monitor import TrafficMonitor
from .capture import PacketCaptureManager
from .config import load_config
from .db import get_connection, init_db, add_system_log
from .discovery import sync_inventory
from .firewall import apply_base_policy, rebuild_whitelist
from .oui_lookup import OUILookup
from .scheduler import RepeatingTask
from .webapp import create_app


def ensure_directories(config: dict) -> None:
    for key in ("captures_dir", "logs_dir"):
        Path(config["paths"][key]).mkdir(parents=True, exist_ok=True)
    Path(config["paths"]["db_path"]).parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    config = load_config()
    ensure_directories(config)

    conn = get_connection(config["paths"]["db_path"])
    init_db(conn)

    add_system_log(conn, "INFO", "System starting up")

    oui_lookup = OUILookup(config["paths"]["oui_file"])

    # Apply firewall base policy and rebuild whitelist rules from DB on startup
    try:
        apply_base_policy()
        rebuild_whitelist(conn)
        add_system_log(conn, "INFO", "Firewall whitelist applied successfully")
    except Exception as exc:
        add_system_log(conn, "WARNING", f"Firewall setup skipped (may need root): {exc}")

    def run_discovery() -> None:
        sync_inventory(conn, config["network"]["ap_interface"], oui_lookup)
        add_system_log(conn, "INFO", f"Device discovery completed on {config['network']['ap_interface']}")

    app = create_app(conn, config)

    should_start_background = (
        not config["app"]["debug"] or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    )

    if should_start_background:
        discovery_task = RepeatingTask(
            interval_seconds=config["monitoring"]["discovery_interval_seconds"],
            target=run_discovery,
            name="device-discovery",
        )
        discovery_task.start()

        capture_manager = PacketCaptureManager(
            conn=conn,
            captures_dir=config["paths"]["captures_dir"],
            tcpdump_bin=config["capture"]["tcpdump_bin"],
        )

        if config["capture"]["enabled"]:
            capture_manager.start(config["network"]["capture_interface"])

        atexit.register(capture_manager.stop)
        atexit.register(lambda: add_system_log(conn, "INFO", "System shutting down"))

        monitor = TrafficMonitor(
            conn=conn,
            interface=config["network"]["capture_interface"],
            bytes_threshold=config["monitoring"]["bytes_per_second_threshold"],
            packets_threshold=config["monitoring"]["packets_per_second_threshold"],
            throttle_rate=config["monitoring"]["throttle_rate"],
            throttle_duration_seconds=config["monitoring"]["throttle_duration_seconds"],
        )

        monitor_task = RepeatingTask(
            interval_seconds=config["monitoring"]["monitoring_interval_seconds"],
            target=monitor.evaluate,
            name="traffic-monitor",
        )

        if config["monitoring"]["enabled"]:
            monitor_task.start()

    add_system_log(conn, "INFO", f"Web dashboard starting on {config['app']['host']}:{config['app']['port']}")
    app.run(
        host=config["app"]["host"],
        port=config["app"]["port"],
        debug=config["app"]["debug"],
    )


if __name__ == "__main__":
    main()