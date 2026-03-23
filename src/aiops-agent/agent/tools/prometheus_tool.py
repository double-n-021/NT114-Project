# tools/prometheus_tool.py
# Agent Tool: query_metrics
#
# Architecture mapping:
#   AI Agent → [this tool] → Prometheus HTTP API
#   Agent uses this tool to OBSERVE system state during ReAct loop

import os
import logging
import requests

logger = logging.getLogger("tool:prometheus")
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9091")

QUERIES = {
    "request_rate": 'sum(rate(http_request_total[1m]))',
    "latency": 'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))',
    "error_rate": 'sum(rate(http_request_total{status_code=~"5.."}[1m])) / sum(rate(http_request_total[1m]))',
}


def _query(promql: str) -> float:
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": promql}, timeout=5
        )
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if results:
            val = results[0]["value"][1]
            return 0.0 if val == "NaN" else float(val)
        return 0.0
    except Exception as e:
        logger.error(f"PromQL failed: {e}")
        return 0.0


def query_metrics(metric_name: str = "all") -> str:
    """Query current system metrics from Prometheus.

    Args:
        metric_name: One of: all, latency, error_rate, request_rate

    Returns:
        Natural language description of current metric values.
    """
    if metric_name == "all":
        results = []
        for name, query in QUERIES.items():
            val = _query(query)
            if name == "latency":
                results.append(f"  - Latency p99: {val*1000:.0f}ms")
            elif name == "error_rate":
                results.append(f"  - Error rate: {val*100:.2f}%")
            else:
                results.append(f"  - Request rate: {val:.1f} req/s")
        return "Current metrics:\n" + "\n".join(results)

    if metric_name in QUERIES:
        val = _query(QUERIES[metric_name])
        return f"{metric_name} = {val}"

    return f"Unknown metric: {metric_name}. Use: all, latency, error_rate, request_rate"
