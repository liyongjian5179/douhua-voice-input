from __future__ import annotations

import signal
import sys
import time
import webbrowser

from douhua_voice.clipboard_guard import ClipboardGuard
from douhua_voice.config import ConfigStore
from douhua_voice.hotkey_listener import HoldKeyListener
from douhua_voice.keyboard_actions import KeyboardActions
from douhua_voice.logging_buffer import LogBuffer
from douhua_voice.orchestrator import VoiceInputOrchestrator
from douhua_voice.web_console import WebConsole


def main() -> None:
    config_store = ConfigStore()
    config = config_store.load()
    logger = LogBuffer()
    keyboard = KeyboardActions()
    clipboard = ClipboardGuard()
    orchestrator = VoiceInputOrchestrator(
        config=config,
        keyboard=keyboard,
        clipboard=clipboard,
        logger=logger,
    )
    listener = HoldKeyListener(
        hold_key=config.hold_key,
        on_press=orchestrator.on_hold_press,
        on_release=orchestrator.on_hold_release,
        hold_threshold_ms=config.hold_threshold_ms,
    )
    # Inject listener into orchestrator so it can toggle ignore_releases_for
    orchestrator.listener = listener
    
    web = WebConsole(
        config_store=config_store,
        config=config,
        logger=logger,
        orchestrator=orchestrator,
        listener=listener,
    )
    web.start()
    url = f"http://{config.web_host}:{config.web_port}"
    logger.append(f"控制台已启动：{url}")
    webbrowser.open(url)

    def shutdown(*_args) -> None:
        orchestrator.stop()
        listener.stop()
        web.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        time.sleep(1)
