from __future__ import annotations

import atexit
import os
from pathlib import Path

from .capture import PacketCaptureManager
from .config import load_config
from .db import get_connection, init_db
from .discovery import sync_inventory
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

    oui_lookup = OUILookup(config["paths"]["oui_file"])

    def run_discovery() -> None:
        sync_inventory(conn, config["network"]["ap_interface"], oui_lookup)

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

    app.run(
        host=config["app"]["host"],
        port=config["app"]["port"],
        debug=config["app"]["debug"],
    )


if __name__ == "__main__":
    main()