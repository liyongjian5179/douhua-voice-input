from __future__ import annotations

import subprocess


class ClipboardGuard:
    def __init__(self) -> None:
        self._snapshot: str | None = None

    def snapshot(self) -> str:
        self._snapshot = self._read_text()
        return self._snapshot

    def restore(self) -> None:
        if self._snapshot is None:
            return
        self._write_text(self._snapshot)
        self._snapshot = None

    def current_text(self) -> str:
        return self._read_text()

    @staticmethod
    def _read_text() -> str:
        proc = subprocess.run(
            ["pbpaste"],
            check=False,
            text=True,
            capture_output=True,
        )
        return proc.stdout

    @staticmethod
    def _write_text(text: str) -> None:
        subprocess.run(
            ["pbcopy"],
            input=text,
            text=True,
            check=False,
            capture_output=True,
        )
