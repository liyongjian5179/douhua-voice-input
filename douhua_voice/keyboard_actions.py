from __future__ import annotations

import time
from typing import Iterable

from pynput.keyboard import Controller, Key


KEY_MAP = {
    "enter": Key.enter,
    "esc": Key.esc,
    "ctrl": Key.ctrl,
    "cmd": Key.cmd,
    "cmd_r": Key.cmd_r,
    "alt": Key.alt,
    "option": Key.alt,
    "d": "d",
}


class KeyboardActions:
    def __init__(self) -> None:
        self.controller = Controller()

    def send_combo(self, combo: str) -> None:
        parts = [self._resolve(p) for p in combo.lower().split("+")]
        self._press_many(parts)

    def send_key(self, key: str) -> None:
        resolved = self._resolve(key)
        self.controller.press(resolved)
        time.sleep(0.05)
        self.controller.release(resolved)

    def _press_many(self, parts: Iterable[object]) -> None:
        pressed: list[object] = []
        for part in parts:
            self.controller.press(part)
            pressed.append(part)
        time.sleep(0.01)
        for part in reversed(pressed):
            self.controller.release(part)

    @staticmethod
    def _resolve(token: str) -> object:
        token = token.strip()
        if token in KEY_MAP:
            return KEY_MAP[token]
        if len(token) == 1:
            return token
        raise ValueError(f"unsupported key token: {token}")
