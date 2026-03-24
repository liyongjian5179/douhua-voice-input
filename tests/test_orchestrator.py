from __future__ import annotations

import time
import unittest

from douhua_voice.config import AppConfig
from douhua_voice.logging_buffer import LogBuffer
from douhua_voice.orchestrator import VoiceInputOrchestrator


class FakeKeyboard:
    def __init__(self) -> None:
        self.combos: list[str] = []
        self.keys: list[str] = []

    def send_combo(self, combo: str) -> None:
        self.combos.append(combo)

    def send_key(self, key: str) -> None:
        self.keys.append(key)


class FakeClipboard:
    def __init__(self) -> None:
        self.snapshot_calls = 0
        self.restore_calls = 0
        self.current_value = "before"
        self.current_calls = 0

    def snapshot(self) -> str:
        self.snapshot_calls += 1
        return self.current_value

    def restore(self) -> None:
        self.restore_calls += 1

    def current_text(self) -> str:
        self.current_calls += 1
        if self.current_calls >= 2:
            return "recognized text"
        return self.current_value


class OrchestratorTest(unittest.TestCase):
    def test_press_release_triggers_combo_submit_restore(self) -> None:
        config = AppConfig(
            normal_delay_ms=10,
            clipboard_restore_delay_ms=10,
            submit_settle_timeout_ms=120,
            post_submit_grace_ms=10,
        )
        logger = LogBuffer()
        keyboard = FakeKeyboard()
        clipboard = FakeClipboard()
        o = VoiceInputOrchestrator(config, keyboard, clipboard, logger)

        o.start()
        o.on_hold_press()
        o.on_hold_release()
        time.sleep(0.2)

        self.assertEqual(clipboard.snapshot_calls, 1)
        self.assertEqual(keyboard.combos, ["ctrl+d"])
        self.assertEqual(keyboard.keys, ["enter"])
        self.assertEqual(clipboard.restore_calls, 1)


if __name__ == "__main__":
    unittest.main()
