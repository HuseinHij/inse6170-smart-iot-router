from __future__ import annotations

import csv
from pathlib import Path


class OUILookup:
    def __init__(self, oui_file: str) -> None:
        self.oui_file = Path(oui_file)
        self.mapping: dict[str, str] = {}
        if self.oui_file.exists():
            self._load()

    def _load(self) -> None:
        with self.oui_file.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                prefix = row["prefix"].strip().upper()
                vendor = row["vendor"].strip()
                self.mapping[prefix] = vendor

    @staticmethod
    def normalize_prefix(mac_address: str) -> str:
        parts = mac_address.upper().replace("-", ":").split(":")
        return ":".join(parts[:3])

    def lookup(self, mac_address: str) -> str:
        prefix = self.normalize_prefix(mac_address)
        return self.mapping.get(prefix, "Unknown vendor")
