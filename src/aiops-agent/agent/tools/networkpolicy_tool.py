# tools/networkpolicy_tool.py
# Agent Tool: apply_network_policy
#
# Architecture mapping:
#   Decision Engine → [this tool] → K8s API Server → NetworkPolicy (medical-data ns)
#   "kubectl apply -f netpol.yaml"
#
# LangChain Tool interface:
#   name:        "apply_network_policy"
#   description: "Block traffic from a suspicious IP CIDR by applying a Kubernetes
#                 NetworkPolicy to the medical-data namespace."
#   input:       cidr (str) — e.g. "10.0.0.5/32"
#   output:      "NetworkPolicy applied: blocked 10.0.0.5/32" or error message
#
# Implementation notes:
#   - Uses kubernetes Python client (not subprocess kubectl)
#   - Loads NetworkPolicy template from templates/networkpolicy_template.yaml
#   - Renders template with blocked CIDR
#   - Applies via K8s API (requires ServiceAccount with RBAC — see k8s/aiops/agent/)
#
# TODO: Implement — see roadmap Bước 5-6
