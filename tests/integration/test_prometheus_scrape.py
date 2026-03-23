# Integration Test: Prometheus → target-app
# Validates that Prometheus successfully scrapes /metrics from target-app
#
# Checks:
#   1. target-app /metrics endpoint returns valid Prometheus format
#   2. Prometheus target status is UP
#   3. Key metrics (http_request_total, http_request_duration_seconds) exist
#
# Run: pytest tests/integration/ -v
# TODO: Implement after Prometheus is deployed
