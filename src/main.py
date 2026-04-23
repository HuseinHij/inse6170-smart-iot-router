import atexit
import os
from pathlib import Path

from .capture import PacketCaptureManager
from .config import load_config
from .db import get_connection, init_db, add_system_log, cleanup_old_records
from .discovery import sync_inventory
from .firewall import apply_base_policy, rebuild_whitelist
from .monitor import TrafficMonitor
from .oui_lookup import OUILookup
from .scheduler import RepeatingTask
from .webapp import create_app


def main():
    config = load_config()

    for key in ("captures_dir", "logs_dir"):
        Path(config["paths"][key]).mkdir(parents=True, exist_ok=True)
    Path(config["paths"]["db_path"]).parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection(config["paths"]["db_path"])
    init_db(conn)
    add_system_log(conn, "INFO", "System starting up")

    oui = OUILookup(config["paths"]["oui_file"])

    try:
        apply_base_policy()
        rebuild_whitelist(conn)
        add_system_log(conn, "INFO", "Firewall rules applied")
    except Exception as e:
        add_system_log(conn, "WARNING", f"Firewall skipped (run as root): {e}")

    cap_manager = PacketCaptureManager(
        conn, config["paths"]["captures_dir"], config["capture"]["tcpdump_bin"]
    )

    app = create_app(conn, config, cap_manager)

    if not config["app"]["debug"] or os.environ.get("WERKZEUG_RUN_MAIN") == "true":

        def run_discovery():
            sync_inventory(conn, config["network"]["ap_interface"], oui)

        RepeatingTask(config["monitoring"]["discovery_interval_seconds"], run_discovery, "discovery").start()

        monitor = TrafficMonitor(
            conn=conn,
            interface=config["network"]["capture_interface"],
            bytes_threshold=config["monitoring"]["bytes_per_second_threshold"],
            packets_threshold=config["monitoring"]["packets_per_second_threshold"],
            throttle_rate=config["monitoring"]["throttle_rate"],
            throttle_duration_seconds=config["monitoring"]["throttle_duration_seconds"],
            ips_capture_seconds=config["monitoring"].get("ips_capture_seconds", 10),
            captures_dir=config["paths"]["captures_dir"],
            tcpdump_bin=config["capture"]["tcpdump_bin"],
            notify_config=config.get("notifications", {}),
        )

        if config["monitoring"]["enabled"]:
            RepeatingTask(config["monitoring"]["monitoring_interval_seconds"], monitor.evaluate, "monitor").start()

        days = config.get("retention", {}).get("history_days", 30)
        interval = config.get("retention", {}).get("cleanup_interval_seconds", 86400)
        RepeatingTask(interval, lambda: cleanup_old_records(conn, days), "cleanup").start()

    add_system_log(conn, "INFO", f"Dashboard running on port {config['app']['port']}")
    app.run(host=config["app"]["host"], port=config["app"]["port"], debug=config["app"]["debug"])


if __name__ == "__main__":
    main()