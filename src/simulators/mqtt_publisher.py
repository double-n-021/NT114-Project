# simulators/mqtt_publisher.py
# ============================================================
# EXTERNAL TRAFFIC SOURCE — MQTT Publisher (PRIORITY: HIGH)
# ============================================================
# Giả lập thiết bị y tế IoT gửi dữ liệu sinh hiệu qua MQTT.
#
# Data flow:
#   Script này → Mosquitto Broker (:1883) → target-app (subscribe vitals/#)
#
# Mỗi "device" publish JSON chứa:
#   - heart_rate: nhịp tim (bpm) — bình thường 60-100
#   - spo2: nồng độ oxy máu (%) — bình thường 95-100
#   - blood_pressure: huyết áp — bình thường 120/80 ± biến thiên
#   - timestamp: thời gian gửi
#
# Usage:
#   python mqtt_publisher.py --broker localhost --port 1883 --devices 5
#   python mqtt_publisher.py --broker <minikube_ip> --port <node_port> --devices 10
# ============================================================

import argparse
import json
import random
import time
import threading

import paho.mqtt.client as mqtt


def generate_vital_signs(device_id, pattern="normal"):
    """
    Tạo dữ liệu sinh hiệu giả lập theo pattern.

    Patterns:
      - normal:      HR 60-100, SpO2 95-100 (bệnh nhân ổn định)
      - tachycardia: HR 100-150, SpO2 90-96 (nhịp tim nhanh bất thường)
      - bradycardia: HR 40-60, SpO2 92-97  (nhịp tim chậm bất thường)

    Returns dict sẵn sàng publish dưới dạng JSON.
    """
    if pattern == "tachycardia":
        hr = random.randint(100, 150)
        spo2 = round(random.uniform(90, 96), 1)
        sys_bp = random.randint(130, 170)
    elif pattern == "bradycardia":
        hr = random.randint(40, 60)
        spo2 = round(random.uniform(92, 97), 1)
        sys_bp = random.randint(90, 110)
    else:  # normal
        hr = random.randint(60, 100)
        spo2 = round(random.uniform(95, 100), 1)
        sys_bp = random.randint(110, 130)

    dia_bp = random.randint(60, 90)

    return {
        "device_id": device_id,
        "heart_rate": hr,
        "spo2": spo2,
        "blood_pressure": f"{sys_bp}/{dia_bp}",
        "timestamp": time.time(),
    }


def device_loop(client, device_id, interval, pattern):
    """
    Vòng lặp chính cho 1 thiết bị — publish dữ liệu mỗi `interval` giây.

    Topic format: vitals/<device_id>
    Ví dụ: vitals/patient_001, vitals/patient_002, ...
    """
    topic = f"vitals/{device_id}"
    print(f"  [DEVICE] {device_id} publishing to {topic} every {interval}s (pattern={pattern})")

    while True:
        data = generate_vital_signs(device_id, pattern)
        payload = json.dumps(data)
        client.publish(topic, payload, qos=1)
        print(f"  [{device_id}] HR={data['heart_rate']} SpO2={data['spo2']} BP={data['blood_pressure']}")
        time.sleep(interval)


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback khi kết nối MQTT thành công/thất bại."""
    if rc == 0:
        print("[MQTT] Connected to broker successfully")
    else:
        print(f"[MQTT] Connection failed with code {rc}")


def main():
    parser = argparse.ArgumentParser(description="MQTT Vital Signs Publisher")
    parser.add_argument("--broker", default="localhost", help="Mosquitto broker IP")
    parser.add_argument("--port", type=int, default=1883, help="Broker port")
    parser.add_argument("--devices", type=int, default=5, help="Số thiết bị giả lập")
    parser.add_argument("--interval", type=float, default=1.0, help="Thời gian giữa 2 lần gửi (giây)")
    parser.add_argument("--pattern", default="normal", choices=["normal", "tachycardia", "bradycardia"],
                        help="Pattern sinh hiệu")
    args = parser.parse_args()

    # --- Kết nối MQTT ---
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    print(f"[MQTT] Connecting to {args.broker}:{args.port} ...")
    client.connect(args.broker, args.port)
    client.loop_start()  # chạy network loop trong background thread

    # --- Spawn 1 thread cho mỗi device ---
    print(f"[MQTT] Starting {args.devices} virtual devices (pattern={args.pattern})")
    threads = []
    for i in range(args.devices):
        device_id = f"patient_{i+1:03d}"
        t = threading.Thread(target=device_loop, args=(client, device_id, args.interval, args.pattern), daemon=True)
        t.start()
        threads.append(t)

    # --- Giữ main thread sống ---
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MQTT] Stopping publisher...")
        client.loop_stop()
        client.disconnect()
        print("[MQTT] Disconnected.")


if __name__ == "__main__":
    main()
