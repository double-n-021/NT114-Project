# tools/networkpolicy_tool.py
# Agent Tool: apply_network_policy
#
# Architecture mapping:
#   Decision Engine → [this tool] → K8s API Server → NetworkPolicy (medical-data ns)
#
# Phase 1 (MVP/Demo): Log action only (simulated)
# Phase 2 (production): Use kubernetes Python client with YAML template

import logging

logger = logging.getLogger("tool:networkpolicy")

_blocked_cidrs: list[str] = []


def apply_network_policy(cidr: str) -> str:
    """Block traffic from a suspicious IP CIDR by applying a Kubernetes NetworkPolicy.

    Args:
        cidr: IP CIDR to block, e.g. "10.0.0.5/32"

    Returns:
        Result message confirming the block action.
    """
    if len(_blocked_cidrs) >= 5:
        return f"ERROR: Maximum 5 CIDRs can be blocked. Currently blocked: {_blocked_cidrs}"

    if cidr in _blocked_cidrs:
        return f"CIDR {cidr} is already blocked"

    _blocked_cidrs.append(cidr)
    msg = f"✅ BLOCKED traffic from {cidr} (NetworkPolicy applied). Total blocked: {len(_blocked_cidrs)}"
    logger.info(msg)

    # TODO Phase 2: Real K8s NetworkPolicy
    # from kubernetes import client, config
    # config.load_incluster_config()
    # ... render template + apply

    return msg


def get_blocked_cidrs() -> list[str]:
    return list(_blocked_cidrs)


def clear_blocked_cidrs():
    _blocked_cidrs.clear()
