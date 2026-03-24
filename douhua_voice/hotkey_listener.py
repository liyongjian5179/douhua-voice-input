from __future__ import annotations

from pynput.keyboard import Key, Listener


class HoldKeyListener:
    def __init__(self, hold_key: str, on_press, on_release, hold_threshold_ms: int = 200) -> None:
        self.hold_key = hold_key
        self.on_press = on_press
        self.on_release = on_release
        self.hold_threshold_ms = hold_threshold_ms
        self._listener: Listener | None = None
        self._pressed = False
        self._press_time = 0.0

    def start(self) -> None:
        if self._listener is not None:
            return
        self._listener = Listener(on_press=self._handle_press, on_release=self._handle_release)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None
        self._pressed = False
        self._press_time = 0.0

    def _handle_press(self, key) -> None:
        if self._pressed:
            return
        if self._match_hold_key(key):
            self._pressed = True
            self._press_time = __import__("time").time()
            # 延迟触发 on_press，只有按住超过阈值才视为长按
            __import__("threading").Timer(self.hold_threshold_ms / 1000.0, self._check_and_trigger_press).start()

    def _check_and_trigger_press(self) -> None:
        if self._pressed:
            self.on_press()

    def _handle_release(self, key) -> None:
        if not self._pressed:
            return
        if self._match_hold_key(key):
            self._pressed = False
            duration = (__import__("time").time() - self._press_time) * 1000
            # 只有当按键持续时间超过阈值时（即已经触发了 on_press），才触发 on_release
            if duration >= self.hold_threshold_ms:
                self.on_release()

    def _match_hold_key(self, key) -> bool:
        if self.hold_key == "cmd_r":
            return key == Key.cmd_r
        if self.hold_key == "cmd":
            return key in {Key.cmd, Key.cmd_l, Key.cmd_r}
        return False
