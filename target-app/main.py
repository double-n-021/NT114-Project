import time
import json
from fastapi import FastAPI, Response
from paho.mqtt import client as mqtt_client
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="Medical Data Collector")

# --- PROMETHEUS METRICS ---
# Đếm tổng số request (dùng để AI phát hiện DDoS)
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
# Đo độ trễ (Mục tiêu QoS < 200ms)
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP Request Latency')

# --- MQTT CONFIG ---
MQTT_BROKER = 'mosquitto-service.medical-data.svc.cluster.local' # DNS nội bộ K8s
MQTT_PORT = 1883
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
    # Thử kết nối MQTT (Local test thì dùng 'localhost')
    try:
        mqtt.connect("localhost", 1883) # Đổi thành MQTT_BROKER khi deploy K8s
        mqtt.loop_start()
    except:
        print("MQTT Broker not available, skipping...")

# --- ENDPOINTS ---

@app.get("/health-check")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/collect")
async def collect_vitals(data: dict):
    REQUEST_COUNT.labels(method='POST', endpoint='/collect', status='200').inc()
    with REQUEST_LATENCY.time():
        # Giả lập xử lý dữ liệu y tế
        print(f"Processing vitals: {data}")
        return {"message": "Data received", "received": data}

@app.get("/metrics")
async def metrics():
    # Endpoint cho Prometheus thu thập dữ liệu
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)