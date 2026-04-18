from __future__ import annotations

from datetime import datetime
from typing import Optional

from .db import add_alert


def create_alert(conn, device_mac: Optional[str], alert_type: str, severity: str, message: str) -> int:
    return add_alert(
        conn=conn,
        device_mac=device_mac,
        alert_type=alert_type,
        severity=severity,
        message=message,
        created_at=datetime.utcnow().isoformat(),
    )
