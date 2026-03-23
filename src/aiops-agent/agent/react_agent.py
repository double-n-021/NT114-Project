# aiops-agent/agent/react_agent.py
# INTELLIGENCE PLANE — Step 2: REASON + PLAN
#
# Architecture mapping:
#   "AI Agent (ReAct) — LangChain + CoT"
#   "Reasoning: Why is latency high? Is this real overload or DDoS? What is the root cause?"
#
# ReAct Pattern (Yao et al., 2022):
#   Thought → Action → Observation → Thought → ... → Final Answer
#
# This module:
#   1. Receives NL context from context_builder.py
#   2. Uses LangChain create_react_agent() with defined tools
#   3. Runs ReAct loop: reason about root cause, select action, observe result
#   4. Outputs validated action(s) to decision_engine.py
#
# Tools available (defined in tools/):
#   - query_metrics:        re-query Prometheus for specific metrics
#   - apply_network_policy: block suspicious IP CIDRs
#   - scale_deployment:     adjust replica count via KEDA ScaledObject
#
# Safety constraints (from architecture):
#   - Maximum 3 actions per cycle
#   - Never scale above 10 replicas
#   - Never block more than 5 CIDRs at once
#   - Always verify recovery within 60 seconds
#
# TODO: Implement — see roadmap Bước 5
