from __future__ import annotations

from collections import deque
from datetime import datetime
from threading import Lock


class LogBuffer:
    def __init__(self, max_lines: int = 500) -> None:
        self._lines: deque[str] = deque(maxlen=max_lines)
        self._lock = Lock()

    def append(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}"
        with self._lock:
            self._lines.append(line)

    def dump(self) -> list[str]:
        with self._lock:
            return list(self._lines)
