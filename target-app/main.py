import os
import time
import json
from fastapi import FastAPI, Response
from paho.mqtt import client as mqtt_client
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="Medical Data Collector")

# --- PROMETHEUS METRICS ---
# Đếm tổng số request (dùng để AI phát hiện DDoS)
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
# Đo độ trễ (Mục tiêu QoS < 200ms)
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP Request Latency')
# Metric nhịp tim (Dùng Gauge vì giá trị này thay đổi lên xuống)
HEART_RATE = Gauge('patient_heart_rate_bpm', 'Current heart rate of the patient', ['patient_id'])

# --- MQTT CONFIG ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto-service.medical-data.svc.cluster.local")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = "medical/vital-signs"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    # Xử lý dữ liệu sinh hiệu từ MQTT
    data = json.loads(msg.payload.decode())
    print(f"Received vital signs via MQTT: {data}")

# Khởi tạo MQTT Client chạy ngầm
mqtt = mqtt_client.Client()
mqtt.on_connect = on_connect
mqtt.on_message = on_message


@app.on_event("startup")
async def startup_event():
    # Thử kết nối MQTT với cơ chế Retry
    retry_count = 0
    max_retries = 10
    connected = False

    while not connected and retry_count < max_retries:
        try:
            print(f"Connecting to MQTT Broker at {MQTT_BROKER} (Attempt {retry_count + 1}/{max_retries})...")
            mqtt.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            mqtt.loop_start()
            connected = True
            print("Successfully scheduled MQTT connection!")
        except Exception as e:
            retry_count += 1
            print(f"Connection failed: {e}. Retrying in 5s...")
            time.sleep(5)

    if not connected:
        print("Could not connect to MQTT Broker after several attempts. Skipping...")

# --- ENDPOINTS ---

@app.get("/health-check")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}


@app.post("/collect")
async def collect_vitals(data: dict):
    # Tăng count khi có request
    REQUEST_COUNT.labels(method='POST', endpoint='/collect', status='200').inc()

    with REQUEST_LATENCY.time():
        hr_value = data.get("heart_rate")
        p_id = data.get("patient_id", "P001")

        if hr_value:
            # GÁN GIÁ TRỊ VÀO METRIC (Đây là bước tạo ra dữ liệu trên Graph)
            HEART_RATE.labels(patient_id=p_id).set(hr_value)
            print(f"Recorded Heart Rate: {hr_value}")

        return {"status": "success", "heart_rate": hr_value}

@app.get("/metrics")
async def metrics():
    # Endpoint cho Prometheus thu thập dữ liệu
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)