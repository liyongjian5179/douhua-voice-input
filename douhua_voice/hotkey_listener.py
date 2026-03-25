from __future__ import annotations

import threading
import time
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
        
        # 保护期：在这个时间戳之前的所有按键释放事件都将被忽略
        # 用于屏蔽我们自己模拟发送快捷键时产生的松开事件
        self._ignore_release_until = 0.0
        
        # Health monitor
        self._running = False
        self._monitor_thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._start_listener()
        
        # Start health monitor
        self._monitor_thread = threading.Thread(target=self._health_monitor, daemon=True)
        self._monitor_thread.start()

    def _start_listener(self) -> None:
        if self._listener is not None:
            self._listener.stop()
        self._listener = Listener(on_press=self._handle_press, on_release=self._handle_release)
        self._listener.start()
        self._pressed = False
        self._press_time = 0.0

    def stop(self) -> None:
        self._running = False
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._pressed = False
        self._press_time = 0.0

    def _health_monitor(self) -> None:
        """
        Periodically checks if the listener thread is still alive.
        If it dies (e.g., due to system sleep/wake or macOS Tap timeout),
        restarts it automatically.
        """
        while self._running:
            if self._listener is not None and not self._listener.is_alive():
                print("[HealthMonitor] Listener died, restarting...")
                self._start_listener()
            time.sleep(2.0)

    def ignore_releases_for(self, seconds: float) -> None:
        """设置一个保护期，期间忽略所有的松开事件"""
        self._ignore_release_until = time.time() + seconds

    def _handle_press(self, key) -> None:
        if self._pressed:
            return
        if self._match_hold_key(key):
            self._pressed = True
            self._press_time = time.time()
            # 延迟触发 on_press，只有按住超过阈值才视为长按
            threading.Timer(self.hold_threshold_ms / 1000.0, self._check_and_trigger_press).start()

    def _check_and_trigger_press(self) -> None:
        if self._pressed:
            self.on_press()

    def _handle_release(self, key) -> None:
        if not self._pressed:
            return
            
        # 保护期内，忽略松开事件（屏蔽模拟按键的影响）
        if time.time() < self._ignore_release_until:
            return
            
        if self._match_hold_key(key):
            self._pressed = False
            self.on_release()

    def _match_hold_key(self, key) -> bool:
        if self.hold_key == "cmd_r":
            return key == Key.cmd_r
        elif self.hold_key == "cmd_l":
            return key == Key.cmd_l
        elif self.hold_key == "cmd":
            return key in {Key.cmd, Key.cmd_l, Key.cmd_r}
        elif self.hold_key == "alt_r" or self.hold_key == "option_r":
            return key == Key.alt_r
        elif self.hold_key == "alt_l" or self.hold_key == "option_l":
            return key == Key.alt_l
        elif self.hold_key == "alt" or self.hold_key == "option":
            return key in {Key.alt, Key.alt_l, Key.alt_r}
        elif self.hold_key == "ctrl_r":
            return key == Key.ctrl_r
        elif self.hold_key == "ctrl_l":
            return key == Key.ctrl_l
        elif self.hold_key == "ctrl":
            return key in {Key.ctrl, Key.ctrl_l, Key.ctrl_r}
        return False
