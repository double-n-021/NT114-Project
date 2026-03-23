# simulators/Dockerfile
# ============================================================
# Container image cho các simulator scripts
# ============================================================
# Dùng để chạy simulator trong Docker/K8s thay vì chạy trực tiếp trên máy.
#
# Image này chứa cả 4 scripts:
#   - mqtt_publisher.py   (giả lập IoMT devices)
#   - noise_generator.py  (giả lập traffic nền)
#   - ddos_simulator.py   (giả lập tấn công DDoS)
#   - run_scenario.py     (điều phối kịch bản E2E)
#
# Cách dùng:
#   docker build -t nt114-simulators .
#
#   # Chạy MQTT Publisher
#   docker run --rm nt114-simulators mqtt_publisher.py --broker <BROKER_IP> --devices 5
#
#   # Chạy Noise Generator
#   docker run --rm nt114-simulators noise_generator.py --target http://<TARGET_IP>:8000 --rate 10 --duration 120
#
#   # Chạy DDoS Simulator
#   docker run --rm nt114-simulators ddos_simulator.py --target http://<TARGET_IP>:8000 --threads 10 --duration 60
#
#   # Chạy kịch bản E2E
#   docker run --rm nt114-simulators run_scenario.py --scenario ddos --target http://<TARGET_IP>:8000
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# Copy và cài dependencies trước (tận dụng Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy tất cả simulator scripts
COPY . .

# ENTRYPOINT = python → CMD truyền tên script + arguments khi docker run
ENTRYPOINT ["python"]
CMD ["--help"]
