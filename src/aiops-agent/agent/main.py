# aiops-agent/agent/main.py
# ============================================================
# INTELLIGENCE PLANE — namespace: aiops
# Main entry point for the Agentic AIOps system
# ============================================================
#
# Supports two modes:
#   v0 (rule-based): Fast, no LLM needed — if/else decision logic
#   v1 (llm-react):  LLM-powered ReAct agent with Ollama
#
# Usage:
#   cd ~/NT114-Project/src/aiops-agent
#
#   # Rule-based (default)
#   python -m agent.main
#
#   # LLM ReAct mode
#   python -m agent.main --mode v1
#
# Environment variables:
#   PROMETHEUS_URL       (default: http://localhost:9091)
#   OLLAMA_HOST          (default: http://localhost:11434)
#   OLLAMA_MODEL         (default: qwen2.5:1.5b)
#   CHECK_INTERVAL       (default: 30)
#   LATENCY_THRESHOLD_MS (default: 200)
#   AGENT_MODE           (default: v0)  — override: v0 | v1
# ============================================================

import argparse
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


def run_cycle_v0(cycle: int):
    """Version 0: Rule-based agent cycle."""
    ctx = build_context()

    decision = rule_based_decide(ctx)
    logger.info(f"🧠 Decision: {decision['action']} — {decision['reason']}")

    if decision["action"] != "NO_ACTION":
        result = execute_action(decision)
        logger.info(f"⚡ Action result: {result}")
    else:
        logger.info("✅ No action needed — system healthy")

    log_entry = {
        "cycle": cycle,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": "v0-rules",
        "metrics": ctx.raw_metrics,
        "anomaly_type": ctx.anomaly_type,
        "decision": decision["action"],
        "reason": decision["reason"],
    }
    logger.info(f"📝 Log: {json.dumps(log_entry, ensure_ascii=False)}")
    return decision


def run_cycle_v1(cycle: int):
    """Version 1: LLM-powered ReAct agent cycle."""
    from .react_agent import run_react_agent

    ctx = build_context()

    if not ctx.has_anomaly:
        logger.info("✅ No anomaly detected — system healthy (skipping LLM)")
        log_entry = {
            "cycle": cycle,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "mode": "v1-llm",
            "metrics": ctx.raw_metrics,
            "anomaly_type": "normal",
            "decision": "NO_ACTION",
            "reason": "All metrics within thresholds",
        }
        logger.info(f"📝 Log: {json.dumps(log_entry, ensure_ascii=False)}")
        return {"action": "NO_ACTION"}

    # Anomaly detected — invoke LLM ReAct agent
    logger.info("🧠 Anomaly detected! Invoking LLM ReAct Agent...")
    result = run_react_agent(ctx.prompt)

    decision_action = result.get("action", "NO_ACTION")
    decision_reason = result.get("reason", "")
    logger.info(f"🤖 LLM Decision: {decision_action} — {decision_reason}")

    # Execute the action
    if decision_action != "NO_ACTION":
        exec_result = execute_action(result)
        logger.info(f"⚡ Action result: {exec_result}")

    # Log with reasoning chain
    log_entry = {
        "cycle": cycle,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": "v1-llm",
        "metrics": ctx.raw_metrics,
        "anomaly_type": ctx.anomaly_type,
        "decision": decision_action,
        "reason": decision_reason,
        "reasoning_steps": len(result.get("reasoning_chain", [])),
    }
    logger.info(f"📝 Log: {json.dumps(log_entry, ensure_ascii=False)}")
    return result


def main():
    """Main agent loop."""
    parser = argparse.ArgumentParser(description="AIOps Agent")
    parser.add_argument(
        "--mode", default=os.environ.get("AGENT_MODE", "v0"),
        choices=["v0", "v1"],
        help="v0=rule-based, v1=LLM ReAct (default: v0)"
    )
    parser.add_argument(
        "--interval", type=int,
        default=CHECK_INTERVAL,
        help=f"Check interval in seconds (default: {CHECK_INTERVAL})"
    )
    args = parser.parse_args()

    mode = args.mode
    interval = args.interval
    mode_label = "Rule-based" if mode == "v0" else "LLM ReAct (Ollama)"

    # Check Ollama availability for v1
    if mode == "v1":
        from .react_agent import check_ollama_available
        if not check_ollama_available():
            logger.warning("⚠️ Ollama not ready. Falling back to v0 (rule-based)")
            logger.warning("   To fix: docker compose exec ollama ollama pull qwen2.5:1.5b")
            mode = "v0"
            mode_label = "Rule-based (Ollama fallback)"

    logger.info("=" * 60)
    logger.info(f"🤖 AIOps Agent starting — mode: {mode_label}")
    logger.info(f"   Prometheus: {os.environ.get('PROMETHEUS_URL', 'http://localhost:9091')}")
    if mode == "v1":
        logger.info(f"   Ollama: {os.environ.get('OLLAMA_HOST', 'http://localhost:11434')}")
        logger.info(f"   Model: {os.environ.get('OLLAMA_MODEL', 'qwen2.5:1.5b')}")
    logger.info(f"   Check interval: {interval}s")
    logger.info(f"   Latency threshold: {LATENCY_THRESHOLD_MS}ms")
    logger.info("=" * 60)

    cycle = 0
    while True:
        cycle += 1
        logger.info(f"\n{'='*40} Cycle {cycle} {'='*40}")

        try:
            if mode == "v0":
                run_cycle_v0(cycle)
            else:
                run_cycle_v1(cycle)
        except KeyboardInterrupt:
            logger.info("\n🛑 Agent stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Agent error in cycle {cycle}: {e}", exc_info=True)

        logger.info(f"💤 Sleeping {interval}s until next cycle...")
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("\n🛑 Agent stopped by user")
            break


if __name__ == "__main__":
    main()
