import requests
import time
import random

TARGET_URL = "http://target-app-service.medical-data.svc.cluster.local/health-check"


def send_noise():
    while True:
        try:
            # Giả lập người dùng bình thường truy cập web
            resp = requests.get(TARGET_URL, timeout=2)
            print(f"Normal User: GET {resp.status_code}")
        except Exception as e:
            print(f"Noise Error: {e}")

        # Nghỉ ngẫu nhiên từ 1 đến 5 giây
        time.sleep(random.uniform(1, 5))


if __name__ == "__main__":
    print("Starting Noise Generator...")
    send_noise()