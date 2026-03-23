# aiops-agent/agent/decision_engine.py
# INTELLIGENCE PLANE — Step 3: DECIDE + ACT
#
# Architecture mapping:
#   "Decision Engine — Priority queue"
#   "1. Block malicious IP first → 2. Scale if still overloaded → 3. Verify recovery"
#   "Safety: max 3 actions/cycle"
#
# This module:
#   1. Receives validated actions from react_agent.py
#   2. Orders actions by priority (block > scale > verify)
#   3. Executes actions via K8s API Server (kubectl apply)
#   4. Logs decision + outcome to MLflow (k8s/aiops/mlflow/)
#
# Priority rules:
#   P1: Block malicious IPs (NetworkPolicy)  — stops attack at source
#   P2: Scale up replicas (ScaledObject)      — handles remaining load
#   P3: Verify recovery (re-check metrics)    — confirm actions worked
#
# TODO: Implement — see roadmap Bước 5
