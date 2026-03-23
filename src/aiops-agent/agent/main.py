# aiops-agent/agent/main.py
# ============================================================
# INTELLIGENCE PLANE — namespace: aiops
# Main entry point for the Agentic AIOps system
# ============================================================
#
# Agent Loop: OBSERVE → REASON → PLAN → ACT → VERIFY
#
#   OBSERVE:  context_builder.py  → queries Prometheus
#   REASON:   decision_engine.py  → rule-based (v0) or LLM ReAct (v1)
#   ACT:      tools/              → scale / block IP (simulated)
#   VERIFY:   re-check metrics next cycle
#
# Usage:
#   cd ~/NT114-Project/src
#   source ../venv/bin/activate
#   python -m aiops-agent.agent.main
#
# Environment variables:
#   PROMETHEUS_URL       (default: http://localhost:9091)
#   CHECK_INTERVAL       (default: 30)
#   LATENCY_THRESHOLD_MS (default: 200)
# ============================================================

import os
import sys
import time
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("aiops-agent")

from .context_builder import build_context
from .decision_engine import rule_based_decide, execute_action

CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "30"))
LATENCY_THRESHOLD_MS = float(os.environ.get("LATENCY_THRESHOLD_MS", "200"))


def main():
    """Main agent loop — runs continuously."""
    logger.info("=" * 60)
    logger.info("🤖 AIOps Agent v0 (Rule-based) starting...")
    logger.info(f"   Prometheus: {os.environ.get('PROMETHEUS_URL', 'http://localhost:9091')}")
    logger.info(f"   Check interval: {CHECK_INTERVAL}s")
    logger.info(f"   Latency threshold: {LATENCY_THRESHOLD_MS}ms")
    logger.info("=" * 60)

    cycle = 0
    while True:
        cycle += 1
        logger.info(f"\n{'='*40} Cycle {cycle} {'='*40}")

        try:
            # Step 1: OBSERVE — query Prometheus metrics
            ctx = build_context()

            # Step 2: REASON + DECIDE — analyze and decide action
            decision = rule_based_decide(ctx)
            logger.info(f"🧠 Decision: {decision['action']} — {decision['reason']}")

            # Step 3: ACT — execute decision
            if decision["action"] != "NO_ACTION":
                result = execute_action(decision)
                logger.info(f"⚡ Action result: {result}")
            else:
                logger.info("✅ No action needed — system healthy")

            # Step 4: LOG — record decision (simple log, MLflow in v1)
            log_entry = {
                "cycle": cycle,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "metrics": ctx.raw_metrics,
                "anomaly_type": ctx.anomaly_type,
                "decision": decision["action"],
                "reason": decision["reason"],
            }
            logger.info(f"📝 Log: {json.dumps(log_entry, ensure_ascii=False)}")

        except KeyboardInterrupt:
            logger.info("\n🛑 Agent stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Agent error in cycle {cycle}: {e}", exc_info=True)

        logger.info(f"💤 Sleeping {CHECK_INTERVAL}s until next cycle...")
        try:
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("\n🛑 Agent stopped by user")
            break


if __name__ == "__main__":
    main()
