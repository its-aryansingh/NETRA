"""
NETRA Remediation Policy Engine.
Pure Python policy guard providing deterministic safety checks before proposing
remediations and immediately before executing mutating AWS API calls.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
from netra.models import PricedResource


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    rule_id: str


def check(
    action: str,
    resource: Union[PricedResource, Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
) -> PolicyDecision:
    """
    Evaluates proposed or executing remediation action against deterministic safety rules.
    Deny rules evaluate first and ALWAYS win.
    """
    ctx = context or {}
    
    # Extract tags and metadata safely
    if isinstance(resource, PricedResource):
        tags = resource.tags or {}
        inr_hour = resource.inr_hour
    elif isinstance(resource, dict):
        tags = resource.get("tags") or {}
        inr_hour = resource.get("inr_hour", 0.0)
    else:
        tags = {}
        inr_hour = 0.0

    action_lower = (action or "").lower().strip()
    is_destructive = action_lower in (
        "terminate",
        "delete",
        "snapshot_and_terminate",
        "snapshot_and_delete",
    )
    bare_destructive = action_lower in ("terminate", "delete")

    # 1. Deny Rule: forbid_protected (any action on netra:protected resource)
    if "netra:protected" in tags and tags["netra:protected"] is not None:
        return PolicyDecision(
            allowed=False,
            reason="Resource carries netra:protected tag.",
            rule_id="forbid_protected",
        )

    # 2. Deny Rule: forbid_dependents (cannot destroy resource with attached dependents)
    dep_count = ctx.get("dependent_count", 0)
    if is_destructive and dep_count > 0:
        return PolicyDecision(
            allowed=False,
            reason=f"Resource has {dep_count} active dependents (target groups, route tables, or ELBs).",
            rule_id="forbid_dependents",
        )

    # 3. Deny Rule: forbid_unsnapshotted (cannot bare-terminate without snapshot step)
    has_snapshot = ctx.get("has_snapshot_step", False) or "snapshot" in action_lower
    if bare_destructive and not has_snapshot:
        return PolicyDecision(
            allowed=False,
            reason="Destructive termination requires an explicit volume snapshot step.",
            rule_id="forbid_unsnapshotted",
        )

    # 4. Permit Rule: permit_owner (owners may stop, downsize, or pause)
    owner = tags.get("Owner")
    if owner and action_lower in ("stop", "downsize", "none"):
        return PolicyDecision(
            allowed=True,
            reason=f"Owner '{owner}' authorized non-destructive {action_lower}.",
            rule_id="permit_owner",
        )

    # 5. Permit Rule: permit_owner_destructive (destructive action with snapshot permitted)
    if is_destructive and has_snapshot:
        return PolicyDecision(
            allowed=True,
            reason="Destructive operation verified with safeguarding snapshot step.",
            rule_id="permit_owner_destructive" if owner else "permit_destructive_with_snapshot",
        )

    # 6. Default fallback permit for benign actions
    if action_lower in ("stop", "none", "downsize"):
        return PolicyDecision(
            allowed=True,
            reason=f"Benign operation '{action_lower}' satisfies baseline guardrails.",
            rule_id="permit_standard",
        )

    return PolicyDecision(
        allowed=True,
        reason="Remediation policy checks passed.",
        rule_id="permit_default",
    )


def explain(decision: PolicyDecision) -> str:
    """Returns human-readable text suitable for UI and audit logs."""
    verdict = "Permitted" if decision.allowed else "Denied"
    return f"{verdict} by {decision.rule_id}: {decision.reason}"
