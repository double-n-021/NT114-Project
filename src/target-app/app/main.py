# target-app/app/main.py
# ============================================================
# DATA PLANE — namespace: medical-data
# FastAPI service nhận dữ liệu sinh hiệu và expose Prometheus metrics
# ============================================================
# Architecture mapping:
#   - POST /collect    → nhận dữ liệu từ MQTT subscriber & HTTP clients
#   - GET  /health-check → liveness/readiness probe cho K8s
#   - GET  /metrics    → Prometheus scrape endpoint (ServiceMonitor CRD)
#
# Khi startup:
#   - Tự động khởi chạy MQTT Subscriber (background thread)
#   - Subscribe topic vitals/# để nhận dữ liệu sinh hiệu từ IoMT devices
# ============================================================

import asyncio
import random
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from .metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    REQUESTS_IN_PROGRESS,
    generate_latest_metrics,
)
from .mqtt_subscriber import init_subscriber


# --- Lifespan Event ---
# Đây là cách FastAPI hiện đại quản lý startup/shutdown events.
# Khi app khởi động → chạy init_subscriber() để bắt đầu nhận MQTT data.
@asynccontextmanager
async def lifespan(app):
    # === STARTUP ===
    print("[APP] Starting up...")
    init_subscriber()  # Khởi chạy MQTT subscriber background thread
    print("[APP] Ready to receive traffic")
    yield
    # === SHUTDOWN ===
    print("[APP] Shutting down...")


app = FastAPI(
    title="Target App - Medical Data Service",
    lifespan=lifespan,  # Gắn lifespan event vào app
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Instrument mỗi HTTP request cho Prometheus metrics."""
    # Bỏ qua endpoint /metrics (tránh metrics đo chính nó)
    if request.url.path == "/metrics":
        return await call_next(request)

    method = request.method
    endpoint = request.url.path

    REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
    start_time = asyncio.get_event_loop().time()

    response = await call_next(request)

    duration = asyncio.get_event_loop().time() - start_time
    status_code = str(response.status_code)

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
    REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()

    return response


@app.get("/health-check")
def health():
    return {"status": "online"}


@app.post("/collect")
async def collect_data(data: dict):
    """
    Nhận dữ liệu sinh hiệu từ HTTP clients (noise, ddos, hoặc forward từ MQTT).

    SỬA LỖI: time.sleep() → asyncio.sleep()
    - time.sleep() là BLOCKING → khóa toàn bộ event loop của FastAPI
    - asyncio.sleep() là NON-BLOCKING → cho phép xử lý nhiều requests đồng thời
    - Khi bị DDoS (hàng trăm requests/s), blocking sleep làm sai lệch kết quả latency
    """
    # Giả lập thời gian xử lý dữ liệu (10-50ms)
    processing_time = random.uniform(0.01, 0.05)
    await asyncio.sleep(processing_time)  # ✅ Non-blocking (trước đó là time.sleep — blocking)
    return {
        "status": "received",
        "process_time": f"{processing_time:.4f}s",
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Prometheus scrape endpoint.
    ServiceMonitor CRD trong k8s/medical-data/ trỏ tới endpoint này.
    """
    return generate_latest_metrics()
