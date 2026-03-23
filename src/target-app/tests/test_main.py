# Tests for target-app
# Validates: /health-check, /collect, /metrics endpoints
#
# Run: pytest src/target-app/tests/ -v

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health-check")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_collect_data():
    response = client.post("/collect", json={
        "device_id": "patient_001",
        "heart_rate": 72,
        "timestamp": 1708300000.0,
    })
    assert response.status_code == 200
    assert response.json()["status"] == "received"


def test_metrics_endpoint():
    """Verify /metrics returns Prometheus format with expected metric names."""
    # Send a request first to generate metrics
    client.post("/collect", json={"device_id": "test", "heart_rate": 70})

    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "http_request_total" in body
    assert "http_request_duration_seconds" in body
