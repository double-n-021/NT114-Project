# aiops-agent/agent/main.py
# ============================================================
# INTELLIGENCE PLANE — namespace: aiops
# Main entry point for the Agentic AIOps system
# ============================================================
#
# Full Agent Loop (theo đề cương kiến trúc):
#   ① OBSERVE  → context_builder.py (query Prometheus)
#   ② REASON   → decision_engine.py (v0) / react_agent.py (v1)
#   ③ PLAN     → priority queue (Block > Scale > NoAction)
#   ④ ACT      → tools/ (execute action)
#   ⑤ VERIFY   → re-query metrics, check recovery
#              → Retry Loop (max 3 actions/cycle)
#
# Usage:
#   cd ~/NT114-Project/src/aiops-agent
#   python -m agent.main            # v0 (rule-based)
#   python -m agent.main --mode v1  # v1 (LLM ReAct)
#
# Environment variables:
#   PROMETHEUS_URL       (default: http://localhost:9091)
#   OLLAMA_HOST          (default: http://localhost:11434)
#   OLLAMA_MODEL         (default: qwen2.5:1.5b)
#   CHECK_INTERVAL       (default: 30)
#   VERIFY_WAIT          (default: 15)
#   MAX_RETRIES          (default: 3)
#   LATENCY_THRESHOLD_MS (default: 200)
#   AGENT_MODE           (default: v0)
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
VERIFY_WAIT = int(os.environ.get("VERIFY_WAIT", "15"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
LATENCY_THRESHOLD_MS = float(os.environ.get("LATENCY_THRESHOLD_MS", "200"))


def _reason(mode: str, ctx, cycle: int) -> dict:
    """Step ②③: REASON + PLAN — chọn action dựa trên mode."""
    if mode == "v0":
        return rule_based_decide(ctx)
    else:
        from .react_agent import run_react_agent
        if not ctx.has_anomaly:
            return {"action": "NO_ACTION", "reason": "All metrics within thresholds"}
        return run_react_agent(ctx.prompt)


def _verify_action(decision: dict, attempt: int) -> dict:
    """Step ⑤: VERIFY — re-query Prometheus, kiểm tra recovery."""
    logger.info(f"🔍 VERIFY (attempt {attempt}): Waiting {VERIFY_WAIT}s to re-check metrics...")
    time.sleep(VERIFY_WAIT)

    ctx_after = build_context()
    verify_result = {
        "attempt": attempt,
        "metrics_before_action": decision.get("_metrics_before", {}),
        "metrics_after_action": ctx_after.raw_metrics,
        "still_anomaly": ctx_after.has_anomaly,
        "anomaly_type_after": ctx_after.anomaly_type,
    }

    if not ctx_after.has_anomaly:
        verify_result["status"] = "SUCCESS"
        logger.info(
            f"✅ VERIFY SUCCESS: System recovered! "
            f"rate={ctx_after.request_rate:.1f} req/s, "
            f"p99={ctx_after.latency_p99*1000:.0f}ms, "
            f"err={ctx_after.error_rate*100:.1f}%"
        )
    else:
        verify_result["status"] = "RETRY"
        logger.warning(
            f"⚠️ VERIFY RETRY: System still anomalous ({ctx_after.anomaly_type}). "
            f"rate={ctx_after.request_rate:.1f} req/s, "
            f"p99={ctx_after.latency_p99*1000:.0f}ms"
        )

    return verify_result


def run_cycle(mode: str, cycle: int) -> dict:
    """Full Agent Cycle: OBSERVE → REASON → PLAN → ACT → VERIFY (+ Retry)."""
    mode_label = "v0-rules" if mode == "v0" else "v1-llm"
    action_log = []

    # ① OBSERVE
    ctx = build_context()

    # Nếu hệ thống bình thường → NO_ACTION, không cần VERIFY
    if not ctx.has_anomaly:
        if mode == "v1":
            logger.info("✅ No anomaly detected — system healthy (skipping LLM)")
        else:
            logger.info("✅ No action needed — system healthy")

        log_entry = {
            "cycle": cycle,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "mode": mode_label,
            "metrics": ctx.raw_metrics,
            "anomaly_type": "normal",
            "decision": "NO_ACTION",
            "reason": "All metrics within thresholds",
            "verify": "SKIPPED",
            "retry_count": 0,
        }
        logger.info(f"📝 Log: {json.dumps(log_entry, ensure_ascii=False)}")
        return {"action": "NO_ACTION"}

    # === RETRY LOOP (max 3 actions/cycle) — theo đề cương ===
    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(f"\n--- Action attempt {attempt}/{MAX_RETRIES} ---")

        # ② REASON + ③ PLAN
        decision = _reason(mode, ctx, cycle)
        decision["_metrics_before"] = ctx.raw_metrics
        logger.info(f"🧠 Decision: {decision.get('action')} — {decision.get('reason', '')}")

        # ④ ACT
        if decision.get("action", "NO_ACTION") != "NO_ACTION":
            result = execute_action(decision)
            logger.info(f"⚡ Action result: {result}")

            # ⑤ VERIFY
            verify = _verify_action(decision, attempt)
            action_log.append({
                "attempt": attempt,
                "decision": decision.get("action"),
                "reason": decision.get("reason", ""),
                "verify_status": verify["status"],
                "metrics_after": verify["metrics_after_action"],
            })

            if verify["status"] == "SUCCESS":
                # Recovery thành công → thoát retry loop
                break
            else:
                # Chưa recover → re-observe rồi thử lại
                logger.info(f"🔄 Retry: re-observing system for next attempt...")
                ctx = build_context()
                if not ctx.has_anomaly:
                    logger.info("✅ System recovered during retry check")
                    break
        else:
            # Agent quyết định NO_ACTION (dù có anomaly) → không cần verify
            action_log.append({
                "attempt": attempt,
                "decision": "NO_ACTION",
                "reason": decision.get("reason", ""),
                "verify_status": "SKIPPED",
            })
            break

    # === LOG kết quả toàn bộ cycle ===
    final_status = action_log[-1]["verify_status"] if action_log else "SKIPPED"
    log_entry = {
        "cycle": cycle,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": mode_label,
        "metrics_initial": ctx.raw_metrics,
        "anomaly_type": ctx.anomaly_type,
        "total_attempts": len(action_log),
        "final_status": final_status,
        "actions": action_log,
    }
    logger.info(f"📝 Cycle Log: {json.dumps(log_entry, ensure_ascii=False)}")

    return decision


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
    logger.info(f"   Verify wait: {VERIFY_WAIT}s")
    logger.info(f"   Max retries/cycle: {MAX_RETRIES}")
    logger.info(f"   Latency threshold: {LATENCY_THRESHOLD_MS}ms")
    logger.info("=" * 60)

    cycle = 0
    while True:
        cycle += 1
        logger.info(f"\n{'='*40} Cycle {cycle} {'='*40}")

        try:
            run_cycle(mode, cycle)
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
