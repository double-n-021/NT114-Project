# aiops-agent/agent/context_builder.py
# INTELLIGENCE PLANE — Step 1: OBSERVE
#
# Architecture mapping:
#   Prometheus (TSDB) → [this module] → AI Agent
#   "Aggregate metrics 30s window, convert numbers to NL prompt, inject system context"

import os
import logging
import requests
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("context-builder")

PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9091")
LATENCY_THRESHOLD = float(os.environ.get("LATENCY_THRESHOLD_MS", "200")) / 1000


@dataclass
class SystemContext:
    """Kết quả quan sát hệ thống — 5 metrics theo đề cương."""
    request_rate: float = 0.0
    latency_p99: float = 0.0
    error_rate: float = 0.0
    cpu_usage: float = 0.0           # CPU usage % (process-level)
    has_anomaly: bool = False
    anomaly_type: str = "normal"  # normal | high_load | ddos_suspected | high_error_rate
    prompt: str = ""
    raw_metrics: dict = field(default_factory=dict)


def _query_prometheus(query: str) -> Optional[float]:
    """Query PromQL và trả về giá trị scalar."""
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if results:
            val = results[0]["value"][1]
            # Handle NaN
            if val == "NaN":
                return 0.0
            return float(val)
        return 0.0
    except Exception as e:
        logger.warning(f"Prometheus query failed: {query} → {e}")
        return None


def build_context() -> SystemContext:
    """Query tất cả metrics và xây dựng context cho Agent."""
    ctx = SystemContext()

    # === Query metrics ===
    ctx.request_rate = _query_prometheus(
        'sum(rate(http_request_total[1m]))'
    ) or 0.0

    ctx.latency_p99 = _query_prometheus(
        'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))'
    ) or 0.0

    err_rate = _query_prometheus(
        'sum(rate(http_request_total{status_code=~"5.."}[1m])) / sum(rate(http_request_total[1m]))'
    )
    ctx.error_rate = err_rate if err_rate and err_rate > 0 else 0.0

    # CPU usage (process-level) — theo đề cương
    ctx.cpu_usage = _query_prometheus(
        'rate(process_cpu_seconds_total{job="target-app"}[1m]) * 100'
    ) or 0.0

    ctx.raw_metrics = {
        "request_rate": round(ctx.request_rate, 2),
        "latency_p99_ms": round(ctx.latency_p99 * 1000, 1),
        "error_rate_pct": round(ctx.error_rate * 100, 2),
        "cpu_usage_pct": round(ctx.cpu_usage, 1),
    }

    # === Phát hiện anomaly ===
    # Rule 1: Latency vượt ngưỡng
    if ctx.latency_p99 > LATENCY_THRESHOLD:
        ctx.has_anomaly = True
        if ctx.request_rate > 100:
            ctx.anomaly_type = "ddos_suspected"
        else:
            ctx.anomaly_type = "high_load"
    # Rule 2: Request rate bất thường cao (detect DDoS TRƯỚC KHI latency tăng)
    elif ctx.request_rate > 100:
        ctx.has_anomaly = True
        ctx.anomaly_type = "ddos_suspected"
    # Rule 3: Error rate cao
    elif ctx.error_rate > 0.01:
        ctx.has_anomaly = True
        ctx.anomaly_type = "high_error_rate"
    # Rule 4: CPU usage quá cao (> 80%)
    elif ctx.cpu_usage > 80:
        ctx.has_anomaly = True
        ctx.anomaly_type = "high_load"

    # === Tạo NL prompt cho LLM ===
    ctx.prompt = _build_prompt(ctx)

    logger.info(
        f"Context: rate={ctx.request_rate:.1f} req/s, "
        f"p99={ctx.latency_p99*1000:.0f}ms, "
        f"err={ctx.error_rate*100:.1f}%, "
        f"cpu={ctx.cpu_usage:.1f}%, "
        f"anomaly={ctx.anomaly_type}"
    )
    return ctx


def _build_prompt(ctx: SystemContext) -> str:
    """Chuyển metrics thành NL prompt cho LLM."""
    status = "⚠️ ANOMALY DETECTED" if ctx.has_anomaly else "✅ NORMAL"
    latency_note = "→ VIOLATION" if ctx.latency_p99 > LATENCY_THRESHOLD else "→ OK"
    error_note = "→ HIGH" if ctx.error_rate > 0.01 else "→ OK"
    cpu_note = "→ HIGH" if ctx.cpu_usage > 80 else "→ OK"

    return f"""Current system status (last 60s):
- Status: {status}
- Request rate: {ctx.request_rate:.1f} req/s
- Latency p99: {ctx.latency_p99*1000:.0f}ms (threshold: 200ms) {latency_note}
- Error rate: {ctx.error_rate*100:.2f}% {error_note}
- CPU usage: {ctx.cpu_usage:.1f}% (threshold: 80%) {cpu_note}
- Anomaly type: {ctx.anomaly_type}

As the AIOps Agent, analyze these metrics and decide:
1. Is this a DDoS attack or legitimate high load?
2. What action should be taken? Options:
   - SCALE_UP: Increase replicas (for legitimate overload)
   - BLOCK_IP: Apply NetworkPolicy to block suspicious IPs (for DDoS)
   - NO_ACTION: System is healthy
3. Explain your reasoning step by step.

Respond in this exact JSON format:
{{"action": "SCALE_UP|BLOCK_IP|NO_ACTION", "reason": "...", "details": {{}}}}
"""
