# target-app/app/mqtt_subscriber.py
# ============================================================
# MQTT Subscriber Module — nhận dữ liệu sinh hiệu từ IoMT devices
# ============================================================
# Architecture mapping:
#   mqtt_publisher.py → Mosquitto Broker (:1883) → MODULE NÀY (subscribe vitals/#)
#   Đây là CRITICAL DATA PATH cho dữ liệu sinh hiệu thời gian thực
#
# Chức năng:
#   1. Kết nối tới Mosquitto broker
#   2. Subscribe topic: vitals/# (nhận tất cả dữ liệu từ mọi patient)
#   3. Parse JSON payload từ IoMT devices
#   4. Cập nhật Prometheus metrics (từ metrics.py) để AI Agent quan sát
#
# Dependencies: paho-mqtt==2.1.0
# ============================================================

import json
import os
import threading
import time

import paho.mqtt.client as mqtt

from .metrics import REQUEST_COUNT, REQUEST_LATENCY

# Đọc cấu hình từ biến môi trường (environment variables)
# → Khi chạy local: dùng giá trị mặc định (localhost:1883)
# → Khi chạy trên K8s: set env trong deployment.yaml
BROKER_HOST = os.environ.get("MQTT_BROKER", "localhost")
BROKER_PORT = int(os.environ.get("MQTT_PORT", "1883"))
TOPIC = "vitals/#"


def on_connect(client, userdata, flags, rc, properties=None):
    """
    Callback khi kết nối MQTT thành công.

    Tại sao subscribe ở đây thay vì ở ngoài?
    → Nếu mất kết nối rồi reconnect, on_connect sẽ được gọi lại
    → Tự động re-subscribe, không bị mất topic
    """
    if rc == 0:
        print(f"[MQTT-SUB] Connected to {BROKER_HOST}:{BROKER_PORT}")
        print(f"[MQTT-SUB] Subscribing to topic: {TOPIC}")
        client.subscribe(TOPIC, qos=1)
    else:
        print(f"[MQTT-SUB] Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """
    Callback khi nhận được message MQTT từ IoMT device.

    Flow:
      1. Parse JSON payload (heart_rate, spo2, blood_pressure, ...)
      2. In ra log để debug
      3. Cập nhật Prometheus metrics:
         - REQUEST_COUNT: đếm số message nhận được (method="MQTT")
         - REQUEST_LATENCY: đo thời gian xử lý message
    """
    start_time = time.time()

    try:
        # Parse JSON từ IoMT device
        data = json.loads(msg.payload.decode("utf-8"))

        # Log dữ liệu nhận được (giúp debug)
        device_id = data.get("device_id", "unknown")
        heart_rate = data.get("heart_rate", "N/A")
        spo2 = data.get("spo2", "N/A")
        print(f"  [MQTT-SUB] {msg.topic}: device={device_id} HR={heart_rate} SpO2={spo2}")

        # Cập nhật Prometheus metrics — ĐÂY LÀ PHẦN QUAN TRỌNG
        # AI Agent sẽ query các metrics này qua PromQL để biết:
        #   - Có bao nhiêu message MQTT đang đến?
        #   - Thời gian xử lý mỗi message là bao lâu?
        duration = time.time() - start_time
        REQUEST_COUNT.labels(method="MQTT", endpoint=msg.topic, status_code="200").inc()
        REQUEST_LATENCY.labels(method="MQTT", endpoint=msg.topic).observe(duration)

    except json.JSONDecodeError as e:
        print(f"  [MQTT-SUB] Invalid JSON on {msg.topic}: {e}")
        REQUEST_COUNT.labels(method="MQTT", endpoint=msg.topic, status_code="400").inc()
    except Exception as e:
        print(f"  [MQTT-SUB] Error processing {msg.topic}: {e}")
        REQUEST_COUNT.labels(method="MQTT", endpoint=msg.topic, status_code="500").inc()


def _run_subscriber():
    """
    Hàm nội bộ — chạy MQTT client loop (blocking).
    Được gọi trong background thread để không block FastAPI.
    """
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print(f"[MQTT-SUB] Connecting to {BROKER_HOST}:{BROKER_PORT} ...")
        client.connect(BROKER_HOST, BROKER_PORT)
        # loop_forever() sẽ block thread này và tự reconnect khi mất kết nối
        client.loop_forever()
    except ConnectionRefusedError:
        print(f"[MQTT-SUB] ERROR: Cannot connect to broker at {BROKER_HOST}:{BROKER_PORT}")
        print(f"[MQTT-SUB] Make sure Mosquitto is running!")
    except Exception as e:
        print(f"[MQTT-SUB] ERROR: {e}")


def init_subscriber():
    """
    Khởi chạy MQTT subscriber trong background thread.

    Được gọi khi FastAPI startup (trong main.py lifespan event).
    Dùng daemon=True → thread tự dừng khi main process tắt.
    """
    thread = threading.Thread(target=_run_subscriber, daemon=True)
    thread.start()
    print("[MQTT-SUB] Subscriber started in background thread")
