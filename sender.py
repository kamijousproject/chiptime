import requests
import json
from datetime import datetime

SERVER_URL = "https://forwardstudio.co.th/rfid_event/api/server-reciver.php"

def send_to_server(events: list):
    payload = {
        "source": "chiptime-localhost",
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "events": events
    }

    try:
        r = requests.post(
            SERVER_URL,
            headers={
                "Content-Type": "application/json",
                "X-Source": "chiptime-localhost"
            },
            data=json.dumps(payload),
            timeout=2
        )

        with open("logs/sender.log", "a") as f:
            f.write(f"{datetime.now()} HTTP:{r.status_code}\n")

    except Exception as e:
        with open("logs/sender.log", "a") as f:
            f.write(f"{datetime.now()} ERROR:{str(e)}\n")
