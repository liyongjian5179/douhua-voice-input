from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from douhua_voice.clipboard_guard import ClipboardGuard
from douhua_voice.config import AppConfig
from douhua_voice.keyboard_actions import KeyboardActions
from douhua_voice.logging_buffer import LogBuffer


@dataclass
class RuntimeState:
    running: bool = False
    recording: bool = False
    active_session_id: int = 0
    baseline_clipboard_text: str = ""


class VoiceInputOrchestrator:
    def __init__(
        self,
        config: AppConfig,
        keyboard: KeyboardActions,
        clipboard: ClipboardGuard,
        logger: LogBuffer,
    ) -> None:
        self.config = config
        self.keyboard = keyboard
        self.clipboard = clipboard
        self.logger = logger
        self.state = RuntimeState()
        self._lock = threading.Lock()
        self.listener = None  # 将在 app.py 中注入

    def on_hold_press(self) -> None:
        with self._lock:
            if not self.state.running or self.state.recording:
                return
            self.state.recording = True
            self.state.active_session_id += 1
            sid = self.state.active_session_id
        baseline_text = self.clipboard.snapshot()
        with self._lock:
            self.state.baseline_clipboard_text = baseline_text
        self.logger.append(f"会话#{sid} 开始：触发豆包语音快捷键")
        
        # 保护期：让 listener 在接下来的一小段时间内忽略所有的松开事件
        # 这可以防止我们模拟发送的 Ctrl+D 中的松开事件被误认为是物理按键的松开
        if getattr(self, "listener", None) is not None:
            self.listener.ignore_releases_for(0.3)
            
        self.keyboard.send_combo(self.config.trigger_combo)

    def on_hold_release(self) -> None:
        with self._lock:
            if not self.state.running or not self.state.recording:
                return
            self.state.recording = False
            sid = self.state.active_session_id
            baseline_text = self.state.baseline_clipboard_text
        self.logger.append(f"会话#{sid} 结束：准备提交识别结果")
        delay = self.config.normal_delay_ms / 1000
        restore_delay = self.config.clipboard_restore_delay_ms / 1000
        settle_timeout = self.config.submit_settle_timeout_ms / 1000
        post_submit_grace = self.config.post_submit_grace_ms / 1000
        threading.Thread(
            target=self._submit_and_restore,
            args=(sid, delay, restore_delay, settle_timeout, post_submit_grace, baseline_text),
            daemon=True,
        ).start()

    def _submit_and_restore(
        self,
        sid: int,
        delay: float,
        restore_delay: float,
        settle_timeout: float,
        post_submit_grace: float,
        baseline_text: str,
    ) -> None:
        # 增加松开后的初始缓冲：给豆包悬浮窗完成当前句子识别的收尾时间
        time.sleep(delay)
        
        # 第一次尝试：发一个回车，触发豆包确认识别结果
        self.keyboard.send_key(self.config.submit_key)
        
        # 等待剪贴板变化（豆包识别成功通常会把结果放进剪贴板）
        changed = self._wait_for_clipboard_change(baseline_text, settle_timeout)
        
        if not changed:
            self.logger.append(f"会话#{sid} 警告：剪贴板在 {settle_timeout}s 内未发生变化，可能未说话，尝试发送取消按键 ({self.config.cancel_key})...")
            # 补救机制：如果长时间没有拿到结果，很可能是用户按了快捷键但没说话，此时发送 Esc 关闭豆包录音
            self.keyboard.send_key(self.config.cancel_key)
            
            # 由于没有识别结果，我们直接恢复剪贴板并结束，不执行任何粘贴操作
            time.sleep(restore_delay)
            self.clipboard.restore()
            self.logger.append(f"会话#{sid} 完成：已取消插入并恢复原始剪贴板")
            return
        else:
            self.logger.append(f"会话#{sid} 剪贴板已正常更新，等待豆包原生粘贴完成")
            # 去除主动 Cmd+V，因为豆包客户端自身会在一定条件下自动执行粘贴
            # 如果我们这里再主动发送，就会导致粘贴两次。
            # 我们只需要在这里等待一段足够的时间(post_submit_grace)，
            # 让豆包的原生粘贴把剪贴板里的识别结果打到屏幕上，然后再恢复原来的剪贴板。

        # 粘贴后等待一段时间，确保文本真正落到了目标输入框里
        time.sleep(post_submit_grace)
        time.sleep(restore_delay)
        self.clipboard.restore()
        self.logger.append(f"会话#{sid} 完成：已提交并恢复原始剪贴板")

    def _wait_for_clipboard_change(self, baseline_text: str, timeout_seconds: float) -> bool:
        start = time.time()
        while time.time() - start < timeout_seconds:
            latest = self.clipboard.current_text()
            if latest != baseline_text:
                return True
            time.sleep(0.05)
        return False

    def start(self) -> None:
        with self._lock:
            self.state.running = True
        self.logger.append("语音输入已启动")

    def stop(self) -> None:
        with self._lock:
            self.state.running = False
            self.state.recording = False
        self.logger.append("语音输入已停止")
