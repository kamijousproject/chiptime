#!/usr/bin/env python3
"""
ChipTime Control Panel - รวม UI + RFID Receiver ในไฟล์เดียว
รันด้วย: python3 control.py
เปิดเบราว์เซอร์: http://localhost:8080
"""

from flask import Flask, request, jsonify, render_template_string
import subprocess
import os
import signal
import sys
from datetime import datetime

app = Flask(__name__)

# ===== Config =====
LOG_DIR = "logs"
RECEIVER_PORT = 8081
CONTROL_PORT = 8080
PID_FILE = "receiver.pid"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(LOG_DIR, exist_ok=True)

# ===== Helpers =====
def get_log_tail(name: str, lines: int = 100) -> str:
    path = os.path.join(LOG_DIR, name)
    if not os.path.exists(path):
        return "(no log file)"
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        all_lines = f.readlines()
        return "".join(all_lines[-lines:])

def is_receiver_running() -> bool:
    """Check if receiver process is running"""
    pid_path = os.path.join(SCRIPT_DIR, PID_FILE)
    if not os.path.exists(pid_path):
        return False
    try:
        with open(pid_path) as f:
            pid = int(f.read().strip())
        # Check if process exists
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError, FileNotFoundError):
        # Clean up stale pid file
        if os.path.exists(pid_path):
            os.remove(pid_path)
        return False

def start_receiver():
    """Start receiver.py as subprocess"""
    if is_receiver_running():
        return False, "Already running"
    
    receiver_script = os.path.join(SCRIPT_DIR, "receiver.py")
    log_file = os.path.join(SCRIPT_DIR, LOG_DIR, "startup.log")
    
    # Start receiver.py as background process
    with open(log_file, "a") as log:
        proc = subprocess.Popen(
            [sys.executable, receiver_script],
            cwd=SCRIPT_DIR,
            stdout=log,
            stderr=log,
            start_new_session=True
        )
    
    # Save PID
    pid_path = os.path.join(SCRIPT_DIR, PID_FILE)
    with open(pid_path, "w") as f:
        f.write(str(proc.pid))
    
    return True, f"Started (PID: {proc.pid}) on port {RECEIVER_PORT}"

def stop_receiver():
    """Stop receiver process"""
    pid_path = os.path.join(SCRIPT_DIR, PID_FILE)
    if not is_receiver_running():
        return False, "Not running"
    
    try:
        with open(pid_path) as f:
            pid = int(f.read().strip())
        
        # Kill process group to ensure all child processes are killed
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        os.remove(pid_path)
        return True, "Stopped"
    except Exception as e:
        # Force kill
        try:
            os.kill(pid, signal.SIGKILL)
            os.remove(pid_path)
            return True, "Force stopped"
        except:
            return False, f"Error: {e}"

# ===== Control Panel UI =====
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChipTime Control Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; font-size: 2rem; }
        h1 span { color: #00d9ff; }
        .card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .status-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 20px;
        }
        .status-indicator { display: flex; align-items: center; gap: 12px; }
        .status-dot {
            width: 16px; height: 16px; border-radius: 50%;
            background: #ff4757; box-shadow: 0 0 10px #ff4757;
            animation: pulse 2s infinite;
        }
        .status-dot.running { background: #2ed573; box-shadow: 0 0 10px #2ed573; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .status-text { font-size: 1.2rem; }
        .status-text .info { font-size: 0.85rem; color: #888; }
        .btn-group { display: flex; gap: 12px; flex-wrap: wrap; }
        .btn {
            padding: 12px 28px; border: none; border-radius: 8px;
            font-size: 1rem; font-weight: 600; cursor: pointer;
            transition: all 0.3s; display: flex; align-items: center; gap: 8px;
        }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-start { background: linear-gradient(135deg, #2ed573, #17c964); color: #fff; }
        .btn-start:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(46, 213, 115, 0.4); }
        .btn-stop { background: linear-gradient(135deg, #ff4757, #ff3344); color: #fff; }
        .btn-stop:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(255, 71, 87, 0.4); }
        .btn-refresh { background: rgba(255,255,255,0.2); color: #fff; }
        .btn-refresh:hover { background: rgba(255,255,255,0.3); }
        .log-section h3 { margin-bottom: 15px; display: flex; align-items: center; justify-content: space-between; }
        .log-tabs { display: flex; gap: 8px; }
        .log-tab {
            padding: 6px 16px; border: none; border-radius: 20px;
            background: rgba(255,255,255,0.1); color: #fff;
            cursor: pointer; font-size: 0.9rem; transition: all 0.3s;
        }
        .log-tab.active { background: #00d9ff; color: #1a1a2e; }
        .log-content {
            background: #0d1117; border-radius: 8px; padding: 16px;
            height: 400px; overflow-y: auto;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.85rem; line-height: 1.6;
            white-space: pre-wrap; word-break: break-all; color: #8b949e;
        }
        .message { padding: 12px 16px; border-radius: 8px; margin-bottom: 15px; display: none; }
        .message.success { background: rgba(46, 213, 115, 0.2); border: 1px solid #2ed573; color: #2ed573; display: block; }
        .message.error { background: rgba(255, 71, 87, 0.2); border: 1px solid #ff4757; color: #ff4757; display: block; }
        .info-box {
            background: rgba(0, 217, 255, 0.1); border: 1px solid rgba(0, 217, 255, 0.3);
            border-radius: 8px; padding: 16px; margin-top: 20px;
        }
        .info-box h4 { color: #00d9ff; margin-bottom: 8px; }
        .info-box code { background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; font-size: 0.9rem; }
        .stats { display: flex; gap: 20px; margin-top: 10px; }
        .stat { background: rgba(0,0,0,0.2); padding: 10px 16px; border-radius: 8px; }
        .stat-value { font-size: 1.5rem; font-weight: bold; color: #00d9ff; }
        .stat-label { font-size: 0.8rem; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏷️ <span>ChipTime</span> Control Panel</h1>
        
        <div id="message" class="message"></div>
        
        <div class="card status-card">
            <div class="status-indicator">
                <div id="statusDot" class="status-dot {{ 'running' if running else '' }}"></div>
                <div class="status-text">
                    <div id="statusText">{{ 'Receiver Running' if running else 'Receiver Stopped' }}</div>
                    <div class="info" id="portInfo">{{ 'Port: ' + port|string if running else '' }}</div>
                </div>
            </div>
            <div class="btn-group">
                <button class="btn btn-start" id="btnStart" onclick="startReceiver()" {{ 'disabled' if running else '' }}>▶ Start</button>
                <button class="btn btn-stop" id="btnStop" onclick="stopReceiver()" {{ '' if running else 'disabled' }}>⬛ Stop</button>
                <button class="btn btn-refresh" onclick="location.reload()">🔄 Refresh</button>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="eventCount">{{ events }}</div>
                <div class="stat-label">Events Processed</div>
            </div>
        </div>
        
        <div class="card log-section">
            <h3>
                📋 Logs
                <div class="log-tabs">
                    <button class="log-tab active" onclick="switchLog('receiver')">Receiver</button>
                    <button class="log-tab" onclick="switchLog('sender')">Sender</button>
                    <button class="log-tab" onclick="switchLog('impinj')">Impinj Raw</button>
                </div>
            </h3>
            <div id="logContent" class="log-content">Loading...</div>
        </div>
        
        <div class="info-box">
            <h4>ℹ️ วิธีใช้งาน</h4>
            <p>1. กด <strong>Start</strong> เพื่อเริ่ม RFID Receiver</p>
            <p>2. ตั้งค่า Impinj Reader ให้ส่ง webhook มาที่: <code>http://YOUR_IP:8081/</code></p>
            <p>3. ดู logs ด้านบนเพื่อตรวจสอบการทำงาน</p>
        </div>
    </div>
    
    <script>
        let currentLog = 'receiver';
        
        function showMessage(text, type) {
            const msg = document.getElementById('message');
            msg.textContent = text;
            msg.className = 'message ' + type;
            setTimeout(() => msg.className = 'message', 3000);
        }
        
        async function apiCall(action) {
            const res = await fetch('/api/' + action, { method: 'POST' });
            return res.json();
        }
        
        async function startReceiver() {
            const btn = document.getElementById('btnStart');
            btn.disabled = true;
            btn.textContent = 'Starting...';
            const result = await apiCall('start');
            showMessage(result.message, result.success ? 'success' : 'error');
            setTimeout(() => location.reload(), 1000);
        }
        
        async function stopReceiver() {
            const btn = document.getElementById('btnStop');
            btn.disabled = true;
            btn.textContent = 'Stopping...';
            const result = await apiCall('stop');
            showMessage(result.message, result.success ? 'success' : 'error');
            setTimeout(() => location.reload(), 1000);
        }
        
        async function loadLogs() {
            const res = await fetch('/api/logs?type=' + currentLog);
            const data = await res.json();
            const logDiv = document.getElementById('logContent');
            logDiv.textContent = data.content;
            logDiv.scrollTop = logDiv.scrollHeight;
        }
        
        function switchLog(type) {
            currentLog = type;
            document.querySelectorAll('.log-tab').forEach(btn => {
                btn.classList.toggle('active', btn.textContent.toLowerCase().includes(type));
            });
            loadLogs();
        }
        
        async function updateStats() {
            const res = await fetch('/api/status');
            const data = await res.json();
            document.getElementById('eventCount').textContent = data.events;
        }
        
        loadLogs();
        setInterval(loadLogs, 3000);
        setInterval(updateStats, 2000);
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        running=is_receiver_running(),
        port=RECEIVER_PORT,
        events=0
    )

@app.route("/api/start", methods=["POST"])
def api_start():
    success, msg = start_receiver()
    return jsonify({"success": success, "message": msg})

@app.route("/api/stop", methods=["POST"])
def api_stop():
    success, msg = stop_receiver()
    return jsonify({"success": success, "message": msg})

@app.route("/api/status")
def api_status():
    return jsonify({
        "running": is_receiver_running(),
        "events": 0
    })

@app.route("/api/logs")
def api_logs():
    log_type = request.args.get("type", "receiver")
    content = get_log_tail(f"{log_type}.log", 100)
    return jsonify({"content": content})

# ===== Main =====
if __name__ == "__main__":
    print("=" * 50)
    print("ChipTime Control Panel")
    print("=" * 50)
    print(f"Control Panel: http://localhost:{CONTROL_PORT}")
    print(f"RFID Receiver: http://localhost:{RECEIVER_PORT} (after Start)")
    print("=" * 50)
    print("กด Ctrl+C เพื่อหยุดโปรแกรม")
    print()
    
    app.run(host="0.0.0.0", port=CONTROL_PORT, threaded=True)
