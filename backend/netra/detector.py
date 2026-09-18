"""NETRA deterministic anomaly detector module.

A pure function: no AWS calls or external network requests.
Takes an inventory snapshot, historical baselines, declarative rules,
and metrics, and deterministically computes Findings matching §CONTRACTS.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import statistics
import time
from typing import Any, Dict, List, Optional, Set, Union

import yaml

from netra.models import Finding, PricedResource


def load_rules(rules_source: Optional[Union[str, Path, Dict[str, Any], List[Dict[str, Any]]]] = None) -> List[Dict[str, Any]]:
    """Load detection rules from YAML file path, dict, or list."""
    if rules_source is None:
        rules_path = Path(__file__).parent / "rules.yaml"
        with open(rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("rules", [])
    if isinstance(rules_source, (str, Path)):
        with open(rules_source, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("rules", [])
    if isinstance(rules_source, dict):
        return rules_source.get("rules", [])
    return list(rules_source)


def _get_nested(obj: Any, path: str) -> Any:
    """Extract nested attributes using dot notation (e.g. 'tags.Owner')."""
    parts = path.split(".")
    curr = obj
    for p in parts:
        if isinstance(curr, dict):
            curr = curr.get(p)
        elif hasattr(curr, p):
            curr = getattr(curr, p)
        else:
            return None
    return curr


def check_cond(cond: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Evaluate a single rule condition against context. Compact evaluator."""
    val = _get_nested(context, cond["field"])
    op = cond.get("operator", "eq")
    target = cond.get("value")

    if op == "eq": return val == target
    if op == "ne": return val != target
    if op == "gt": return val is not None and val > target
    if op == "gte": return val is not None and val >= target
    if op == "lt": return val is not None and val < target
    if op == "lte": return val is not None and val <= target
    if op == "in": return target is not None and val in target
    if op == "not_in": return target is not None and val not in target
    if op == "exists": return val is not None and val != ""
    if op == "not_exists": return val is None or val == ""
    if op == "gt_multiple_of":
        ref_val = _get_nested(context, cond.get("ref", ""))
        return (val is not None and ref_val is not None and val > (ref_val * target))
    return False


def evaluate_rule_conditions(rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Evaluate 'all' and 'any' condition blocks of a rule."""
    if "all" in rule:
        if not all(check_cond(c, context) for c in rule["all"]):
            return False
    if "any" in rule:
        if not any(check_cond(c, context) for c in rule["any"]):
            return False
    return True


def generate_finding_id(resource_id: str, detected_at: int) -> str:
    """Generate deterministic 26-character Crockford Base32 ULID from resource and timestamp."""
    digest = hashlib.sha256(f"{resource_id}:{detected_at}".encode("utf-8")).hexdigest()
    crockford = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    num = int(digest, 16)
    chars = []
    for _ in range(26):
        chars.append(crockford[num % 32])
        num //= 32
    return "".join(reversed(chars))


def evaluate(
    snapshot: Union[List[PricedResource], Dict[str, Any]],
    baseline_history: List[Union[float, Dict[str, Any]]],
    rules: Optional[Union[str, Path, Dict[str, Any], List[Dict[str, Any]]]] = None,
    metrics: Optional[Dict[str, Dict[str, Any]]] = None,
    detected_at: Optional[int] = None,
    open_finding_resource_ids: Optional[Set[str]] = None,
    credits_remaining_usd: float = 200.0,
    account_id: str = "default",
) -> List[Finding]:
    """Pure evaluation function computing deterministic Findings from snapshot and metrics.

    - Computes rolling median baseline from last 60 snapshot totals.
    - If fewer than 10 snapshots in history, skips account-scope rules.
    - Dedupes against open_finding_resource_ids.
    - Generates 100% reproducible Finding IDs.
    """
    now_ts = detected_at if detected_at is not None else 1789740918
    open_ids = set(open_finding_resource_ids or [])
    metrics_map = metrics or {}
    all_rules = load_rules(rules)

    # Normalize snapshot resources
    if isinstance(snapshot, dict):
        raw_resources = snapshot.get("resources", [])
    else:
        raw_resources = snapshot

    resources: List[PricedResource] = []
    for r in raw_resources:
        if isinstance(r, PricedResource):
            resources.append(r)
        else:
            resources.append(PricedResource.from_dict(r))

    total_inr_hour = round(sum(r.inr_hour for r in resources), 2)

    # Compute rolling median baseline from up to last 60 snapshot totals
    history_totals: List[float] = []
    for item in baseline_history[-60:]:
        if isinstance(item, (int, float)):
            history_totals.append(float(item))
        elif isinstance(item, dict) and "total_inr_hour" in item:
            history_totals.append(float(item["total_inr_hour"]))

    has_sufficient_history = len(history_totals) >= 10
    baseline_inr_hour = (
        round(statistics.median(history_totals), 2)
        if history_totals
        else total_inr_hour
    )
    delta_inr_hour = round(total_inr_hour - baseline_inr_hour, 2)

    # Separate account-scope and resource-scope rules
    account_rules = [r for r in all_rules if r.get("scope") == "account"]
    resource_rules = [r for r in all_rules if r.get("scope", "resource") == "resource"]

    # Track fired account rules
    fired_account_rules: List[Dict[str, str]] = []
    if has_sufficient_history:
        account_context = {
            "total_inr_hour": total_inr_hour,
            "baseline_inr_hour": baseline_inr_hour,
            "delta_inr_hour": delta_inr_hour,
        }
        for rule in account_rules:
            if evaluate_rule_conditions(rule, account_context):
                fired_account_rules.append({
                    "rule": rule["id"],
                    "detail": f"total_inr_hour={total_inr_hour} baseline={baseline_inr_hour} delta={delta_inr_hour}",
                })

    findings: List[Finding] = []

    # Sort resources deterministically by resource_id to guarantee pure reproducibility
    sorted_resources = sorted(resources, key=lambda x: x.resource_id)

    # Find highest burn resource to attribute account step change if any fired
    highest_burn_res = (
        max(sorted_resources, key=lambda x: x.inr_hour)
        if sorted_resources
        else None
    )

    for res in sorted_resources:
        if res.resource_id in open_ids:
            continue

        res_metrics = metrics_map.get(res.resource_id, {})
        # Build evaluation context combining resource attributes and CloudWatch metrics
        context: Dict[str, Any] = {
            "resource_id": res.resource_id,
            "kind": res.kind,
            "sub_type": res.sub_type,
            "region": res.region,
            "launched_at": res.launched_at,
            "age_seconds": res.age_seconds,
            "usd_hour": res.usd_hour,
            "inr_hour": res.inr_hour,
            "price_ref": res.price_ref,
            "tags": res.tags,
            "state": res.state,
            "meta": res.meta,
            "cpu_max_pct": res_metrics.get("cpu_max_pct", 0.0),
            "network_packets_out": res_metrics.get("network_packets_out", 0),
            "bytes_out": res_metrics.get("bytes_out", 0),
        }

        fired_for_resource: List[Dict[str, str]] = []
        highest_severity = "info"
        severity_rank = {"info": 1, "warning": 2, "critical": 3}

        # If this is highest burn resource and account step change fired, attach it
        if fired_account_rules and highest_burn_res and res.resource_id == highest_burn_res.resource_id:
            for ar in fired_account_rules:
                fired_for_resource.append(ar)
                highest_severity = "critical"

        for rule in resource_rules:
            if evaluate_rule_conditions(rule, context):
                sev = rule.get("severity", "info")
                # Check for downgrade condition
                if "downgrade_when" in rule and "downgrade_to" in rule:
                    if check_cond(rule["downgrade_when"], context):
                        sev = rule["downgrade_to"]

                if severity_rank.get(sev, 1) > severity_rank.get(highest_severity, 1):
                    highest_severity = sev

                # Construct detail string
                detail = f"kind={res.kind} age={res.age_seconds // 60}m"
                if "cpu_max_pct" in context and res.kind == "ec2":
                    detail = f"cpu_max={context['cpu_max_pct']} age={res.age_seconds // 60}m"
                elif res.kind == "ebs":
                    detail = f"unattached size_gb={res.meta.get('size_gb', 0)}"
                elif res.kind == "nat":
                    detail = f"bytes_out={context.get('bytes_out', 0)}"

                fired_for_resource.append({"rule": rule["id"], "detail": detail})

        if fired_for_resource:
            runway = (
                round(credits_remaining_usd / res.usd_hour, 1)
                if res.usd_hour > 0
                else 999.9
            )
            share_pct = (
                round((res.inr_hour / total_inr_hour) * 100.0, 1)
                if total_inr_hour > 0
                else 0.0
            )
            multiple = (
                round(total_inr_hour / baseline_inr_hour, 2)
                if baseline_inr_hour > 0
                else 1.0
            )

            computed_block = {
                "inr_hour": round(res.inr_hour, 2),
                "inr_month": round(res.inr_hour * 730.0, 2),
                "baseline_inr_hour": round(baseline_inr_hour, 2),
                "multiple": multiple,
                "runway_hours": runway,
                "share_of_burn_pct": share_pct,
            }

            fid = generate_finding_id(res.resource_id, now_ts)
            findings.append(
                Finding(
                    finding_id=fid,
                    severity=highest_severity,
                    status="DETECTED",
                    rules_fired=fired_for_resource,
                    resource=res,
                    computed=computed_block,
                    detected_at=now_ts,
                    account_id=account_id,
                )
            )

    return findings
