from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppConfig:
    trigger_combo: str = "option+d"
    submit_key: str = "enter"
    cancel_key: str = "esc"
    hold_key: str = "cmd_r"
    cold_start_delay_ms: int = 200
    hold_threshold_ms: int = 250
    normal_delay_ms: int = 260
    clipboard_restore_delay_ms: int = 220
    submit_settle_timeout_ms: int = 1800
    post_submit_grace_ms: int = 380
    web_host: str = "127.0.0.1"
    web_port: int = 8899


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        default_path = Path.cwd() / ".douhua_voice" / "config.json"
        env_path = os.environ.get("DOUBAO_VOICE_CONFIG")
        resolved = Path(env_path).expanduser() if env_path else default_path
        self.path = path or resolved
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppConfig:
        if not self.path.exists():
            config = AppConfig()
            self.save(config)
            return config
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 兼容旧配置字段
        valid_keys = {f.name for f in AppConfig.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        
        config = AppConfig(**filtered_data)
        
        # 如果有未识别的字段被过滤掉了，或者有新加的字段，保存一下使其保持最新
        if set(data.keys()) != valid_keys:
            self.save(config)
            
        return config

    def save(self, config: AppConfig) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(asdict(config), f, ensure_ascii=False, indent=2)
