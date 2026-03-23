# tools/scale_tool.py
# Agent Tool: scale_deployment
#
# Architecture mapping:
#   Decision Engine → [this tool] → K8s API Server → ScaledObject CRD (medical-data ns)
#
# Phase 1 (MVP/Demo): Log action only (simulated)
# Phase 2 (production): Use kubernetes Python client

import logging

logger = logging.getLogger("tool:scale")

# Track state (simulated)
_current_replicas = 1


def scale_deployment(replicas: int) -> str:
    """Scale the target-app deployment by setting replica count.

    Args:
        replicas: Target replica count (1-10)

    Returns:
        Result message confirming the scale action.
    """
    global _current_replicas

    if not isinstance(replicas, int) or not 1 <= replicas <= 10:
        return f"ERROR: replicas must be integer 1-10, got {replicas}"

    old = _current_replicas
    _current_replicas = replicas
    msg = f"✅ SCALED target-app: {old} → {replicas} replicas"
    logger.info(msg)

    # TODO Phase 2: Real K8s API call
    # from kubernetes import client, config
    # config.load_incluster_config()
    # apps_v1 = client.AppsV1Api()
    # apps_v1.patch_namespaced_deployment_scale(
    #     name="target-app", namespace="medical-data",
    #     body={"spec": {"replicas": replicas}}
    # )

    return msg


def get_current_replicas() -> int:
    return _current_replicas
