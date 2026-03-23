# tools/scale_tool.py
# Agent Tool: scale_deployment
#
# Architecture mapping:
#   Decision Engine → [this tool] → K8s API Server → ScaledObject CRD (medical-data ns)
#   "kubectl apply -f scaledobject.yaml"
#
# LangChain Tool interface:
#   name:        "scale_deployment"
#   description: "Scale the target-app deployment by updating the KEDA ScaledObject
#                 minReplicaCount. Use when organic overload is detected."
#   input:       replicas (int) — target minimum replicas (1-10)
#   output:      "ScaledObject updated: minReplicas=3" or error message
#
# Implementation notes:
#   - Phase 1 (MVP): directly kubectl scale deployment (simple)
#   - Phase 2 (production): update ScaledObject CRD minReplicaCount via K8s API
#   - Uses kubernetes Python client
#   - Requires ServiceAccount with RBAC (see k8s/aiops/agent/)
#
# TODO: Implement — see roadmap Bước 5-6
