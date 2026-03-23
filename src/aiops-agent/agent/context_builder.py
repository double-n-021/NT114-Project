# aiops-agent/agent/context_builder.py
# INTELLIGENCE PLANE — Step 1: OBSERVE
#
# Architecture mapping:
#   Prometheus (TSDB) → [this module] → AI Agent
#   "Aggregate metrics 30s window, convert numbers to NL prompt, inject system context"
#
# This module:
#   1. Queries Prometheus HTTP API with PromQL
#   2. Aggregates results into a 30-second window
#   3. Converts numeric metrics into natural language context
#   4. Outputs a structured prompt that the ReAct Agent can reason about
#
# Key PromQL queries used:
#   - rate(http_request_total[1m])                                    → request rate
#   - histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[1m])) → latency p99
#   - rate(http_request_total{status_code=~"5.."}[1m])               → error rate
#   - count(count by (source_ip)(http_request_total))                 → unique source IPs
#
# Output format (Natural Language prompt for LLM):
#   "Current system status (last 30s):
#    - Request rate: 450 req/s (baseline: 50) → ANOMALY
#    - Latency p99: 380ms (threshold: 200ms) → VIOLATION
#    ..."
#
# TODO: Implement — see roadmap Bước 4
