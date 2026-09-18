"""
NETRA Remediation Policy Engine.
Enforces deterministic safety guardrails using AWS Cedar policy language.
Evaluates proposed remediations against 'policy/netra.cedar' where forbid
rules unconditionally override permit rules.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from netra.models import PricedResource

try:
    import cedarpy
    HAS_CEDARPY = True
except ImportError:
    HAS_CEDARPY = False


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    rule_id: str


# Locate policy files
_POLICY_DIR = Path(__file__).resolve().parent.parent.parent / "policy"
_CEDAR_FILE = _POLICY_DIR / "netra.cedar"
_ENTITIES_FILE = _POLICY_DIR / "entities.json"

_CACHED_POLICIES: Optional[str] = None


def _get_cedar_policies() -> str:
    global _CACHED_POLICIES
    if _CACHED_POLICIES is None:
        if _CEDAR_FILE.exists():
            _CACHED_POLICIES = _CEDAR_FILE.read_text(encoding="utf-8")
        else:
            # Inline fallback copy of policy/netra.cedar
            _CACHED_POLICIES = """
            @id("forbid_protected")
            forbid (principal, action, resource) when { resource.is_protected == true };

            @id("forbid_dependents")
            forbid (principal, action in [Action::"terminate", Action::"delete", Action::"snapshot_and_terminate", Action::"snapshot_and_delete"], resource)
            when { context.dependent_count > 0 };

            @id("forbid_unsnapshotted")
            forbid (principal, action in [Action::"terminate", Action::"delete"], resource)
            unless { context.has_snapshot_step == true };

            @id("permit_owner")
            permit (principal, action in [Action::"stop", Action::"downsize", Action::"none"], resource);

            @id("permit_owner_destructive")
            permit (principal, action in [Action::"terminate", Action::"delete", Action::"snapshot_and_terminate", Action::"snapshot_and_delete"], resource)
            when { context.has_snapshot_step == true };
            """
    return _CACHED_POLICIES


def check(
    action: str,
    resource: Union[PricedResource, Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
) -> PolicyDecision:
    """
    Evaluates proposed remediation action against Cedar safety rules.
    Deny rules evaluate first and ALWAYS win over permit rules.
    """
    ctx = context or {}

    # Extract tags and metadata safely
    if isinstance(resource, PricedResource):
        tags = resource.tags or {}
        resource_id = resource.resource_id
        inr_hour = resource.inr_hour
    elif isinstance(resource, dict):
        tags = resource.get("tags") or {}
        resource_id = resource.get("resource_id", "res-unknown")
        inr_hour = resource.get("inr_hour", 0.0)
    else:
        tags = {}
        resource_id = "res-unknown"
        inr_hour = 0.0

    action_lower = (action or "").lower().strip()
    is_destructive = action_lower in (
        "terminate",
        "delete",
        "snapshot_and_terminate",
        "snapshot_and_delete",
    )
    bare_destructive = action_lower in ("terminate", "delete")
    is_protected = "netra:protected" in tags and tags["netra:protected"] is not None
    dep_count = int(ctx.get("dependent_count", 0))
    has_snapshot = bool(ctx.get("has_snapshot_step", False) or "snapshot" in action_lower)
    owner = tags.get("Owner")

    # 1. Native Cedar Evaluation when cedarpy is available
    if HAS_CEDARPY:
        try:
            policies_text = _get_cedar_policies()
            
            # Map action string to valid Cedar action ID
            clean_act = action_lower if action_lower in (
                "stop", "terminate", "delete", "downsize", "none",
                "snapshot_and_terminate", "snapshot_and_delete"
            ) else "stop"

            req: Dict[str, Any] = {
                "principal": 'User::"operator"',
                "action": f'Action::"{clean_act}"',
                "resource": f'Resource::"{resource_id}"',
                "context": {
                    "dependent_count": dep_count,
                    "has_snapshot_step": has_snapshot,
                },
            }

            entities: List[Dict[str, Any]] = [
                {
                    "uid": {"type": "User", "id": "operator"},
                    "attrs": {"role": "finops_operator"},
                    "parents": [],
                },
                {
                    "uid": {"type": "Action", "id": clean_act},
                    "attrs": {},
                    "parents": [],
                },
                {
                    "uid": {"type": "Resource", "id": resource_id},
                    "attrs": {
                        "is_protected": is_protected,
                        "owner": str(owner or ""),
                    },
                    "parents": [],
                },
            ]

            authz = cedarpy.is_authorized(req, policies_text, entities)

            if authz.decision == cedarpy.Decision.Deny:
                reasons = authz.diagnostics.reasons if hasattr(authz.diagnostics, "reasons") else []
                # Map diagnostic reason to rule id
                if is_protected:
                    return PolicyDecision(
                        allowed=False,
                        reason="Resource carries netra:protected tag.",
                        rule_id="forbid_protected",
                    )
                if is_destructive and dep_count > 0:
                    return PolicyDecision(
                        allowed=False,
                        reason=f"Resource has {dep_count} active dependents (target groups, route tables, or ELBs).",
                        rule_id="forbid_dependents",
                    )
                if bare_destructive and not has_snapshot:
                    return PolicyDecision(
                        allowed=False,
                        reason="Destructive termination requires an explicit volume snapshot step.",
                        rule_id="forbid_unsnapshotted",
                    )
                return PolicyDecision(
                    allowed=False,
                    reason="Operation denied by Cedar security guardrails.",
                    rule_id=reasons[0] if reasons else "forbid_default",
                )
            else:
                # Allowed
                if is_destructive and has_snapshot:
                    return PolicyDecision(
                        allowed=True,
                        reason="Destructive operation verified with safeguarding snapshot step.",
                        rule_id="permit_owner_destructive" if owner else "permit_destructive_with_snapshot",
                    )
                if owner and action_lower in ("stop", "downsize", "none"):
                    return PolicyDecision(
                        allowed=True,
                        reason=f"Owner '{owner}' authorized non-destructive {action_lower}.",
                        rule_id="permit_owner",
                    )
                return PolicyDecision(
                    allowed=True,
                    reason=f"Benign operation '{action_lower}' satisfies baseline guardrails.",
                    rule_id="permit_standard",
                )
        except Exception:
            # Fall through to pure evaluator below
            pass

    # 2. Pure Python fallback evaluator aligned with netra.cedar
    if is_protected:
        return PolicyDecision(
            allowed=False,
            reason="Resource carries netra:protected tag.",
            rule_id="forbid_protected",
        )

    if is_destructive and dep_count > 0:
        return PolicyDecision(
            allowed=False,
            reason=f"Resource has {dep_count} active dependents (target groups, route tables, or ELBs).",
            rule_id="forbid_dependents",
        )

    if bare_destructive and not has_snapshot:
        return PolicyDecision(
            allowed=False,
            reason="Destructive termination requires an explicit volume snapshot step.",
            rule_id="forbid_unsnapshotted",
        )

    if owner and action_lower in ("stop", "downsize", "none"):
        return PolicyDecision(
            allowed=True,
            reason=f"Owner '{owner}' authorized non-destructive {action_lower}.",
            rule_id="permit_owner",
        )

    if is_destructive and has_snapshot:
        return PolicyDecision(
            allowed=True,
            reason="Destructive operation verified with safeguarding snapshot step.",
            rule_id="permit_owner_destructive" if owner else "permit_destructive_with_snapshot",
        )

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
