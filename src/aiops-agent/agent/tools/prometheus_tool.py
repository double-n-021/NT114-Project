# tools/prometheus_tool.py
# Agent Tool: query_metrics
#
# Architecture mapping:
#   AI Agent → [this tool] → Prometheus HTTP API
#   Agent uses this tool to OBSERVE system state during ReAct loop
#
# LangChain Tool interface:
#   name:        "query_metrics"
#   description: "Query current system metrics from Prometheus. Returns request rate,
#                 latency p99, error rate, CPU usage, and source IP distribution."
#   input:       metric_name (str) — one of: all, latency, error_rate, request_rate, cpu
#   output:      Natural language description of current metric values
#
# Prometheus API endpoint:
#   http://monitoring-kube-prometheus-prometheus.monitoring:9090/api/v1/query
#
# TODO: Implement — see roadmap Bước 4-5
