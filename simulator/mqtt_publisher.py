import paho.mqtt.client as mqtt
import json
import time
import random
import os

# Cấu hình từ Environment Variables (Dễ dàng điều chỉnh khi đóng gói Docker)
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "medical/sensors")
PUBLISH_RATE = float(os.getenv("PUBLISH_RATE", 1.0))  # số giây giữa mỗi tin nhắn


def generate_medical_data():
    """Giả lập dữ liệu sinh hiệu thực tế"""
    return {
        "patient_id": f"PATIENT-{random.randint(100, 110)}",
        "heart_rate": random.randint(60, 110),
        "spo2": random.randint(94, 100),
        "blood_pressure": {
            "systolic": random.randint(110, 140),
            "diastolic": random.randint(70, 90)
        },
        "timestamp": time.time()
    }


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT Broker: {MQTT_BROKER}")
    else:
        print(f"Failed to connect, return code {rc}")


# Khởi tạo MQTT Client
client = mqtt.Client()
client.on_connect = on_connect

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    print(f"Starting Simulator - Rate: {PUBLISH_RATE}s/msg")
    while True:
        data = generate_medical_data()
        payload = json.dumps(data)

        # Publish dữ liệu
        result = client.publish(MQTT_TOPIC, payload)
        status = result[0]

        if status == 0:
            print(f"Sent: {payload}")
        else:
            print(f"Failed to send message to topic {MQTT_TOPIC}")

        time.sleep(PUBLISH_RATE)

except KeyboardInterrupt:
    print("\nStopping Simulator...")
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print(f"Error: {e}")