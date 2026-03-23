# target-app/app/metrics.py
# Prometheus instrumentation for target-app
#
# Architecture mapping:
#   These metrics are scraped by Prometheus (INTELLIGENCE PLANE)
#   via ServiceMonitor CRD defined in k8s/medical-data/target-app/servicemonitor.yaml
#
# Metrics exposed:
#   - http_request_total          (Counter)   → feeds: rate() for request rate
#   - http_request_duration_seconds (Histogram) → feeds: histogram_quantile() for latency p99
#   - http_requests_in_progress   (Gauge)     → feeds: current load indicator
#
# These are the PRIMARY INPUT for the Context Builder (src/aiops-agent/agent/context_builder.py)

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# QoS-relevant buckets: 10ms, 25ms, 50ms, 100ms, 200ms (threshold!), 500ms, 1s
LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0)

REQUEST_COUNT = Counter(
    "http_request_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
    buckets=LATENCY_BUCKETS,
)

REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of requests currently being processed",
    ["method", "endpoint"],
)


def generate_latest_metrics() -> bytes:
    """Generate Prometheus text format metrics."""
    return generate_latest()
