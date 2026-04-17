from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import yaml


def load_config(config_path: str = "config/app.yaml") -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)
