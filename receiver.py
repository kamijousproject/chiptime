from flask import Flask, request, jsonify
import json
import os
from datetime import datetime
from sender import send_to_server

app = Flask(__name__)

# ===== config =====
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ===== helpers =====
def log_file(name: str, content: str):
    with open(os.path.join(LOG_DIR, name), "a", encoding="utf-8") as f:
        f.write(content + "\n")

# ===== webhook endpoint =====
@app.route("/", methods=["POST"])
def receive():
    ts_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---- read raw body ----
    raw = request.data.decode("utf-8", errors="ignore")

    # ---- log raw from Impinj ----
    log_file("impinj.log", f"[{ts_local}]\n{raw}\n")

    # ---- parse json ----
    try:
        data = json.loads(raw)
    except Exception:
        # สำคัญ: ห้าม error กลับไป Impinj
        return jsonify({"status": "invalid-json"}), 200

    # ---- Athena ส่งมาเป็น list ที่ root ----
    if isinstance(data, list):
        events_raw = data
    elif isinstance(data, dict):
        events_raw = data.get("events", [])
    else:
        events_raw = []

    normalized_events = []

    # ---- normalize เฉพาะ tagInventory ----
    for e in events_raw:
        if not isinstance(e, dict):
            continue

        if e.get("eventType") != "tagInventory":
            # ข้าม antennaActivation / event อื่น
            continue

        inv = e.get("tagInventoryEvent")
        if not inv:
            continue

        normalized_events.append({
            # ===== fields ที่ server-reciver.php ใช้ =====
            "epc": inv.get("epc"),
            "antenna_port": inv.get("antennaPort"),
            "rssi": inv.get("peakRssiCdbm"),
            "phase": inv.get("phaseAngle"),
            "reader_time": e.get("timestamp"),

            # ===== เก็บ raw เผื่อ debug / replay =====
            "raw": e
        })

    # ---- ส่งต่อไป server ถ้ามี event ----
    if normalized_events:
        send_to_server(normalized_events)
        log_file(
            "receiver.log",
            f"[{ts_local}] sent {len(normalized_events)} events"
        )
    else:
        log_file(
            "receiver.log",
            f"[{ts_local}] no tagInventory event"
        )

    # ---- ตอบ Impinj เสมอ ----
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # ต้อง bind 0.0.0.0 เพื่อให้ Impinj เข้าได้
    app.run(host="0.0.0.0", port=8081)
