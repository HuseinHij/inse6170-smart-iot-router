from __future__ import annotations

import threading
import time
from typing import Callable


class RepeatingTask:
    def __init__(self, interval_seconds: int, target: Callable[[], None], name: str) -> None:
        self.interval_seconds = interval_seconds
        self.target = target
        self.name = name
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.target()
            except Exception as exc:
                print(f"[scheduler:{self.name}] {exc}")
            self._stop.wait(self.interval_seconds)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
