# aiops-agent/agent/decision_engine.py
# INTELLIGENCE PLANE — Step 3: DECIDE + ACT
#
# Architecture mapping:
#   "Decision Engine — Priority queue"
#   "1. Block malicious IP first → 2. Scale if still overloaded → 3. Verify recovery"
#   "Safety: max 3 actions/cycle"

import logging
from .tools.scale_tool import scale_deployment
from .tools.networkpolicy_tool import apply_network_policy

logger = logging.getLogger("decision-engine")

MAX_ACTIONS_PER_CYCLE = 3


def rule_based_decide(ctx) -> dict:
    """Version 0: Quyết định bằng rules đơn giản dựa trên metrics.

    Priority: Block IP (P1) → Scale (P2) → No Action
    """
    if not ctx.has_anomaly:
        return {"action": "NO_ACTION", "reason": "System is healthy — all metrics within thresholds"}

    if ctx.anomaly_type == "ddos_suspected":
        return {
            "action": "BLOCK_IP",
            "reason": (
                f"DDoS suspected: request rate={ctx.request_rate:.0f} req/s (very high), "
                f"p99 latency={ctx.latency_p99*1000:.0f}ms > 200ms threshold"
            ),
            "details": {"cidr": "10.0.0.0/24"},
        }

    if ctx.anomaly_type == "high_load":
        return {
            "action": "SCALE_UP",
            "reason": (
                f"Legitimate high load: p99 latency={ctx.latency_p99*1000:.0f}ms > 200ms, "
                f"but request rate={ctx.request_rate:.0f} req/s is moderate"
            ),
            "details": {"replicas": 3},
        }

    if ctx.anomaly_type == "high_error_rate":
        return {
            "action": "SCALE_UP",
            "reason": f"High error rate: {ctx.error_rate*100:.1f}% > 1% threshold",
            "details": {"replicas": 2},
        }

    return {"action": "NO_ACTION", "reason": f"Anomaly type: {ctx.anomaly_type}, monitoring..."}


def execute_action(decision: dict) -> str:
    """Thực thi action từ quyết định của Agent."""
    action = decision.get("action", "NO_ACTION")
    details = decision.get("details", {})

    if action == "SCALE_UP":
        replicas = details.get("replicas", 3)
        result = scale_deployment(replicas)
        logger.info(f"Executed SCALE_UP: {result}")
        return result

    elif action == "BLOCK_IP":
        cidr = details.get("cidr", "10.0.0.0/24")
        result = apply_network_policy(cidr)
        logger.info(f"Executed BLOCK_IP: {result}")
        return result

    return "No action taken — system healthy"
