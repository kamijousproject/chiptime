# ChipTime - RFID Event Relay Service

ระบบ middleware สำหรับรับข้อมูล RFID จาก Impinj Reader แล้วส่งต่อไปยัง remote server

## สถาปัตยกรรม

```
[Impinj RFID Reader] → [receiver.py:8081] → [sender.py] → [Remote Server]
                              ↑
                    [control.py:8080] (Web UI)
```

## ความต้องการ

- Python 3.x
- Flask
- Requests

```bash
pip install flask requests
```

## ไฟล์ในโปรเจค

| ไฟล์ | คำอธิบาย |
|------|----------|
| `control.py` | Web UI สำหรับควบคุม Start/Stop receiver |
| `receiver.py` | Flask server รับ webhook จาก Impinj Reader |
| `sender.py` | ส่งข้อมูล RFID events ไปยัง remote server |
| `logs/` | โฟลเดอร์เก็บ log files |

## การติดตั้ง

```bash
# Clone repository
git clone https://github.com/kamijousproject/chiptime.git
cd chiptime

# ติดตั้ง dependencies
pip install -r requirements.txt

# สร้างโฟลเดอร์ logs และตั้ง permission
mkdir -p logs
chmod 777 logs
```

## วิธีใช้งาน

### 1. เริ่มต้น Control Panel

```bash
python3 control.py
```

### 2. เปิด Web UI

เปิดเบราว์เซอร์ไปที่: `http://localhost:8080`

### 3. ควบคุม Receiver

- กด **Start** เพื่อเริ่ม RFID Receiver (port 8081)
- กด **Stop** เพื่อหยุด Receiver
- ดู **Logs** แบบ real-time ในหน้าเว็บ

### 4. ตั้งค่า Impinj Reader

ตั้งค่า webhook URL ใน Impinj Reader:
```
http://YOUR_SERVER_IP:8081/
```

## Logs

| Log File | เนื้อหา |
|----------|---------|
| `logs/receiver.log` | บันทึกการรับ events |
| `logs/sender.log` | บันทึกการส่งข้อมูลไป remote server |
| `logs/impinj.log` | Raw data จาก Impinj Reader |
| `logs/startup.log` | Log การเริ่มต้น receiver |

## การตั้งค่า

### Remote Server URL

แก้ไขใน `sender.py`:

```python
SERVER_URL = "https://your-server.com/api/endpoint"
```

### Ports

แก้ไขใน `control.py`:

```python
RECEIVER_PORT = 8081  # Port สำหรับรับ webhook
CONTROL_PORT = 8080   # Port สำหรับ Web UI
```

## Data Format

### ข้อมูลที่รับจาก Impinj (tagInventory event)

```json
{
  "eventType": "tagInventory",
  "timestamp": "2025-12-16T12:00:00Z",
  "tagInventoryEvent": {
    "epc": "E200001234567890",
    "antennaPort": 1,
    "peakRssiCdbm": -450,
    "phaseAngle": 120.5
  }
}
```

### ข้อมูลที่ส่งไป Remote Server

```json
{
  "source": "chiptime-localhost",
  "sent_at": "2025-12-16 12:00:00",
  "events": [
    {
      "epc": "E200001234567890",
      "antenna_port": 1,
      "rssi": -450,
      "phase": 120.5,
      "reader_time": "2025-12-16T12:00:00Z",
      "raw": { ... }
    }
  ]
}
```

## License

MIT
