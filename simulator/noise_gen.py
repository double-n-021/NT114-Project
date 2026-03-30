import requests
import time
import random

# Đổi endpoint sang /collect
TARGET_URL = "http://target-app-service.medical-data.svc.cluster.local/collect"

def send_noise():
    print("Simulator starting...")
    while True:
        try:
            # Giả lập dữ liệu y tế gửi lên
            payload = {
                "patient_id": "P001",
                "heart_rate": random.randint(70, 110) # Nhịp tim ngẫu nhiên
            }
            # Dùng POST thay vì GET
            resp = requests.post(TARGET_URL, json=payload, timeout=2)
            print(f"Sent: {payload['heart_rate']} BPM | Status: {resp.status_code}")
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(2) # Nghỉ 2 giây gửi 1 lần

if __name__ == "__main__":
    send_noise()