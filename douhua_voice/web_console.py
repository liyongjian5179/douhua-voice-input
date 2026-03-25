from __future__ import annotations
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from douhua_voice.config import AppConfig, ConfigStore
from douhua_voice.hotkey_listener import HoldKeyListener
from douhua_voice.logging_buffer import LogBuffer
from douhua_voice.orchestrator import VoiceInputOrchestrator


def html_template() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>豆花语音输入...</title>
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <style>
    :root {
      --bg: #070b16;
      --panel: rgba(17, 25, 40, 0.78);
      --panel-border: rgba(148, 163, 184, 0.2);
      --text-main: #f8fafc;
      --text-sub: #94a3b8;
      --brand: #38bdf8;
      --brand-2: #6366f1;
      --ok: #22c55e;
      --danger: #f97316;
      --log-bg: #030712;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(1100px 580px at -10% -20%, rgba(56, 189, 248, 0.16), transparent 45%),
        radial-gradient(900px 620px at 115% 0%, rgba(99, 102, 241, 0.22), transparent 45%),
        var(--bg);
      color: var(--text-main);
      font-family: "SF Pro Display", "PingFang SC", "Helvetica Neue", sans-serif;
      padding: 28px;
    }
    .wrap {
      max-width: 1060px;
      margin: 0 auto;
      display: grid;
      gap: 18px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 16px;
      backdrop-filter: blur(10px);
      box-shadow: 0 14px 38px rgba(0, 0, 0, 0.28);
    }
    .hero {
      padding: 22px 22px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }
    .title-area {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .logo {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      object-fit: cover;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .title {
      margin: 0;
      font-size: 25px;
      letter-spacing: 0.2px;
      font-weight: 680;
    }
    .subtitle {
      margin-top: 7px;
      color: var(--text-sub);
      font-size: 13px;
    }
    .status {
      border-radius: 999px;
      padding: 8px 13px;
      font-size: 12px;
      font-weight: 650;
      border: 1px solid rgba(148, 163, 184, 0.28);
      color: #cbd5e1;
      background: rgba(15, 23, 42, 0.55);
    }
    .status.running {
      border-color: rgba(34, 197, 94, 0.4);
      color: #bbf7d0;
      background: rgba(34, 197, 94, 0.16);
    }
    .status.stopped {
      border-color: rgba(249, 115, 22, 0.45);
      color: #fed7aa;
      background: rgba(249, 115, 22, 0.14);
    }
    .controls {
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    button {
      border: none;
      border-radius: 12px;
      padding: 10px 18px;
      color: var(--text-main);
      cursor: pointer;
      font-size: 14px;
      font-weight: 650;
      transition: transform .12s ease, box-shadow .2s ease, opacity .2s ease;
    }
    button:active { transform: translateY(1px) scale(0.99); }
    .btn-primary {
      background: linear-gradient(110deg, var(--brand), var(--brand-2));
      box-shadow: 0 10px 22px rgba(14, 165, 233, 0.34);
    }
    .btn-ghost {
      background: rgba(30, 41, 59, 0.72);
      border: 1px solid rgba(148, 163, 184, 0.24);
    }
    .btn-primary:hover, .btn-ghost:hover { opacity: 0.92; }
    .grid {
      padding: 20px 22px 8px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }
    .field {
      background: rgba(15, 23, 42, 0.58);
      border: 1px solid rgba(148, 163, 184, 0.18);
      border-radius: 12px;
      padding: 11px 12px 12px;
    }
    .field label {
      display: block;
      margin-bottom: 2px;
      color: #cbd5e1;
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.2px;
    }
    .field .desc {
      display: block;
      margin-bottom: 8px;
      color: var(--text-sub);
      font-size: 11px;
    }
    .field input {
      width: 100%;
      border-radius: 10px;
      border: 1px solid rgba(148, 163, 184, 0.25);
      background: rgba(2, 6, 23, 0.72);
      color: var(--text-main);
      padding: 9px 10px;
      font-size: 14px;
      outline: none;
    }
    .field input:focus {
      border-color: rgba(56, 189, 248, 0.62);
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
    }
    .save-bar {
      padding: 0 22px 18px;
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }
    .hint {
      color: var(--text-sub);
      font-size: 12px;
    }
    #logs {
      margin: 0;
      white-space: pre-wrap;
      background: var(--log-bg);
      color: #d1e6ff;
      border: 1px solid rgba(56, 189, 248, 0.26);
      border-radius: 14px;
      padding: 14px 15px;
      height: 360px;
      overflow: auto;
      line-height: 1.45;
      font-size: 13px;
      font-family: "SF Mono", "JetBrains Mono", "Menlo", monospace;
    }
    .guide {
      margin-top: 20px;
      padding: 18px 22px;
      background: rgba(56, 189, 248, 0.05);
      border: 1px dashed rgba(56, 189, 248, 0.2);
      border-radius: 14px;
    }
    .guide h3 {
      margin: 0 0 12px 0;
      font-size: 16px;
      color: var(--brand);
    }
    .guide p {
      margin: 6px 0;
      font-size: 13px;
      color: var(--text-sub);
      line-height: 1.6;
    }
    .guide code {
      background: rgba(255, 255, 255, 0.1);
      padding: 2px 6px;
      border-radius: 4px;
      color: #e2e8f0;
      font-family: monospace;
    }
  </style>
</head>
<body>
  <main class="wrap">
    <section class="panel hero">
      <div class="title-area">
        <img src="/douhua-logo.png" alt="Logo" class="logo" />
        <div>
          <h2 class="title">豆花语音输入: 基于豆包APP的语音输入法</h2>
          <div class="subtitle">macOS 控制台 · 按住左 or 右 Command 说话，松开自动写入(骂人)</div>
        </div>
      </div>
      <div class="controls">
        <button class="btn-primary" onclick="startVoice()">启动语音输入</button>
        <button class="btn-ghost" onclick="stopVoice()">停止</button>
        <button class="btn-ghost" onclick="restartVoice()" style="border-color: rgba(249, 115, 22, 0.45); color: #fed7aa;">重启监听器</button>
        <span id="status" class="status stopped">已停止</span>
      </div>
    </section>
    <section class="panel">
      <div class="grid">
        <div class="field">
          <label>hold_key</label>
          <span class="desc">触发语音的长按按键</span>
          <select id="holdKey" style="width: 100%; border-radius: 10px; border: 1px solid rgba(148, 163, 184, 0.25); background: rgba(2, 6, 23, 0.72); color: var(--text-main); padding: 9px 10px; font-size: 14px; outline: none; margin-top: 2px;">
            <option value="cmd_r">右 Command (推荐)</option>
            <option value="cmd_l">左 Command</option>
            <option value="cmd">左右 Command 均可</option>
            <option value="option_r">右 Option</option>
            <option value="option_l">左 Option</option>
            <option value="option">左右 Option 均可</option>
            <option value="ctrl_r">右 Control</option>
            <option value="ctrl_l">左 Control</option>
            <option value="ctrl">左右 Control 均可</option>
          </select>
        </div>
        <div class="field">
          <label>hold_threshold_ms</label>
          <span class="desc">长按唤醒阈值，防误触</span>
          <input id="holdThreshold" type="number" />
        </div>
        <div class="field">
          <label>normal_delay_ms</label>
          <span class="desc">松开后等待豆包识别的缓冲时间</span>
          <input id="normalDelay" type="number" />
        </div>
        <div class="field">
          <label>clipboard_restore_delay_ms</label>
          <span class="desc">恢复原剪贴板的延迟时间</span>
          <input id="restoreDelay" type="number" />
        </div>
        <div class="field">
          <label>submit_settle_timeout_ms</label>
          <span class="desc">等待识别结果写入剪贴板的最大超时</span>
          <input id="settleTimeout" type="number" />
        </div>
        <div class="field">
          <label>post_submit_grace_ms</label>
          <span class="desc">自动粘贴上屏后的安全缓冲时间</span>
          <input id="postSubmitGrace" type="number" />
        </div>
      </div>
      <div class="save-bar">
        <span class="hint">建议先启动后说一句，按实际体感再微调参数</span>
        <div class="controls">
          <button class="btn-ghost" id="toggleLogBtn" onclick="toggleLogs()">隐藏日志</button>
          <button class="btn-primary" onclick="saveConfig()">保存配置</button>
        </div>
      </div>
    </section>
    <section class="panel" id="logSection">
      <pre id="logs"></pre>
    </section>
    
    <section class="panel guide">
      <h3>🚀 使用前必看指南</h3>
      <p>1. <b>配置豆包快捷键</b>：打开「豆包客户端」设置，找到“语音输入”唤醒快捷键，必须设置为 <code>Ctrl + D</code>（因为本程序会在底层帮你自动按这个组合键）。</p>
      <p>2. <b>开启系统辅助功能权限</b>：本程序需要监听你的全局按键以及模拟粘贴。请前往 <code>系统设置 -> 隐私与安全性 -> 辅助功能</code>，在列表中找到你当前运行本程序的终端（如 Terminal、iTerm、Cursor 等）或打包后的 App，并将它<b>勾选允许</b>。</p>
      <p>3. <b>使用方式</b>：配置完成后，在任何需要打字的软件里，<b>长按键盘右侧的 Command 键</b>不放，豆包语音悬浮窗就会弹出。说完话后<b>松开按键</b>，文字就会自动上屏！</p>
    </section>
  </main>
  <script>
    let isEditing = false;
    
    // 监听所有输入框和选择框的聚焦和失焦事件，防止自动刷新覆盖
    document.querySelectorAll('input[type="number"], select').forEach(input => {
      input.addEventListener('focus', () => { isEditing = true; });
      input.addEventListener('blur', () => { isEditing = false; });
      input.addEventListener('change', () => { isEditing = true; }); // 专为 select 增加
    });

    async function req(url, method="GET", body=null) {
      const res = await fetch(url, {method, headers: {"Content-Type":"application/json"}, body: body ? JSON.stringify(body) : null});
      return res.json();
    }
    async function refresh() {
      const d = await req('/api/status');
      const statusEl = document.getElementById('status');
      statusEl.innerText = d.running ? '运行中' : '已停止';
      document.getElementById('status').className = d.running ? 'status running' : 'status stopped';
      
      // 只有在用户没有在输入时，才更新输入框的值，避免打字被打断
      if (!isEditing) {
        document.getElementById('holdKey').value = d.config.hold_key;
        document.getElementById('holdThreshold').value = d.config.hold_threshold_ms;
        document.getElementById('normalDelay').value = d.config.normal_delay_ms;
        document.getElementById('restoreDelay').value = d.config.clipboard_restore_delay_ms;
        document.getElementById('settleTimeout').value = d.config.submit_settle_timeout_ms;
        document.getElementById('postSubmitGrace').value = d.config.post_submit_grace_ms;
      }
      
      document.getElementById('logs').innerText = d.logs.join('\\n');
      document.getElementById('logs').scrollTop = document.getElementById('logs').scrollHeight;
    }
    
    function toggleLogs() {
      const logSec = document.getElementById('logSection');
      const btn = document.getElementById('toggleLogBtn');
      if (logSec.style.display === 'none') {
        logSec.style.display = 'block';
        btn.innerText = '隐藏日志';
      } else {
        logSec.style.display = 'none';
        btn.innerText = '显示日志';
      }
    }

    async function startVoice(){ await req('/api/start', 'POST'); await refresh(); }
    async function stopVoice(){ await req('/api/stop', 'POST'); await refresh(); }
    async function restartVoice(){ 
      const btn = document.querySelector('button[onclick="restartVoice()"]');
      const oldText = btn.innerText;
      btn.innerText = '重启中...';
      await req('/api/restart', 'POST'); 
      await refresh(); 
      btn.innerText = '已重启 ✓';
      setTimeout(() => { btn.innerText = oldText; }, 1500);
    }
    async function saveConfig() {
      await req('/api/config', 'POST', {
        hold_key: document.getElementById('holdKey').value,
        hold_threshold_ms: Number(document.getElementById('holdThreshold').value),
        normal_delay_ms: Number(document.getElementById('normalDelay').value),
        clipboard_restore_delay_ms: Number(document.getElementById('restoreDelay').value),
        submit_settle_timeout_ms: Number(document.getElementById('settleTimeout').value),
        post_submit_grace_ms: Number(document.getElementById('postSubmitGrace').value)
      });
      isEditing = false; // 保存后允许刷新覆盖
      await refresh();
      
      // 保存按钮给予一点视觉反馈
      const btn = document.querySelector('.save-bar .btn-primary');
      const oldText = btn.innerText;
      btn.innerText = '已保存 ✓';
      btn.style.background = '#22c55e';
      setTimeout(() => {
        btn.innerText = oldText;
        btn.style.background = '';
      }, 1500);
    }
    refresh();
    setInterval(refresh, 1000);
  </script>
</body>
</html>
"""


class WebConsole:
    def __init__(
        self,
        config_store: ConfigStore,
        config: AppConfig,
        logger: LogBuffer,
        orchestrator: VoiceInputOrchestrator,
        listener: HoldKeyListener,
    ) -> None:
        self.config_store = config_store
        self.config = config
        self.logger = logger
        self.orchestrator = orchestrator
        self.listener = listener
        self._server: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None

    def start(self) -> None:
        web_console = self

        class Handler(BaseHTTPRequestHandler):
            def _json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _html(self, html: str) -> None:
                body = html.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                if self.path == "/":
                    self._html(html_template())
                    return
                if self.path == "/douhua-logo.png":
                    try:
                        import os
                        logo_path = os.path.join(os.path.dirname(__file__), "douhua-logo.png")
                        with open(logo_path, "rb") as f:
                            body = f.read()
                        self.send_response(HTTPStatus.OK)
                        self.send_header("Content-Type", "image/png")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                    except Exception:
                        self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                    return
                if self.path == "/favicon.svg":
                    import base64
                    import os
                    logo_path = os.path.join(os.path.dirname(__file__), "douhua-logo.png")
                    with open(logo_path, "rb") as f:
                        img_data = f.read()
                    b64_data = base64.b64encode(img_data).decode('utf-8')
                    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><clipPath id="circle"><circle cx="50" cy="50" r="50"/></clipPath><image href="data:image/png;base64,{b64_data}" width="100" height="100" clip-path="url(#circle)" preserveAspectRatio="xMidYMid slice"/></svg>'
                    body = svg.encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "image/svg+xml")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if self.path == "/api/status":
                    self._json(
                        {
                            "running": web_console.orchestrator.state.running,
                            "recording": web_console.orchestrator.state.recording,
                            "config": {
                                "hold_key": web_console.config.hold_key,
                                "hold_threshold_ms": web_console.config.hold_threshold_ms,
                                "normal_delay_ms": web_console.config.normal_delay_ms,
                                "clipboard_restore_delay_ms": web_console.config.clipboard_restore_delay_ms,
                                "submit_settle_timeout_ms": web_console.config.submit_settle_timeout_ms,
                                "post_submit_grace_ms": web_console.config.post_submit_grace_ms,
                            },
                            "logs": web_console.logger.dump(),
                        }
                    )
                    return
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:
                if self.path == "/api/start":
                    web_console.listener.start()
                    web_console.orchestrator.start()
                    self._json({"ok": True})
                    return
                if self.path == "/api/stop":
                    web_console.orchestrator.stop()
                    web_console.listener.stop()
                    self._json({"ok": True})
                    return
                if self.path == "/api/restart":
                    web_console.orchestrator.stop()
                    web_console.listener.stop()
                    import time
                    time.sleep(0.5)
                    web_console.listener.start()
                    web_console.orchestrator.start()
                    self._json({"ok": True})
                    return
                if self.path == "/api/config":
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length) if length else b"{}"
                    payload = json.loads(raw.decode("utf-8"))
                    
                    # Track if we need to restart listener due to key change
                    key_changed = False
                    if "hold_key" in payload and payload["hold_key"] != web_console.config.hold_key:
                        web_console.config.hold_key = payload["hold_key"]
                        key_changed = True
                        
                    if "hold_threshold_ms" in payload:
                        web_console.config.hold_threshold_ms = int(payload["hold_threshold_ms"])
                    if "normal_delay_ms" in payload:
                        web_console.config.normal_delay_ms = int(payload["normal_delay_ms"])
                    if "clipboard_restore_delay_ms" in payload:
                        web_console.config.clipboard_restore_delay_ms = int(payload["clipboard_restore_delay_ms"])
                    if "submit_settle_timeout_ms" in payload:
                        web_console.config.submit_settle_timeout_ms = int(payload["submit_settle_timeout_ms"])
                    if "post_submit_grace_ms" in payload:
                        web_console.config.post_submit_grace_ms = int(payload["post_submit_grace_ms"])
                    web_console.config_store.save(web_console.config)
                    # 同步更新 listener 的长按阈值和按键
                    web_console.listener.hold_threshold_ms = web_console.config.hold_threshold_ms
                    if key_changed:
                        web_console.listener.hold_key = web_console.config.hold_key
                    self._json({"ok": True})
                    return
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

            def log_message(self, *_args) -> None:
                return

        self._server = ThreadingHTTPServer((self.config.web_host, self.config.web_port), Handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
