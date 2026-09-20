"""NETRA FinOps Tag & Budget Governance module.

Provides enterprise FinOps governance:
1. Calculates organization tag allocation compliance scores and unallocated spend.
2. Evaluates real-time burn against monthly budget ceiling thresholds.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from netra.models import PricedResource


DEFAULT_REQUIRED_TAGS = ["Owner", "Environment", "CostCenter"]


def calculate_tag_governance_score(
    resources: List[PricedResource],
    required_tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Calculate tag compliance score and audit untagged billable resources."""
    req_tags = required_tags or DEFAULT_REQUIRED_TAGS
    total_resources = len(resources)
    if total_resources == 0:
        return {
            "score_pct": 100.0,
            "grade": "A",
            "compliant_count": 0,
            "total_resources": 0,
            "unallocated_inr_hour": 0.0,
            "untagged_resources": [],
            "required_tags": req_tags,
        }

    total_tag_slots = total_resources * len(req_tags)
    allocated_slots = 0
    compliant_count = 0
    unallocated_inr = 0.0
    untagged_list: List[Dict[str, Any]] = []

    for res in resources:
        # Check tags case-insensitively
        res_tags = res.tags or {}
        lower_tags = {k.lower(): v for k, v in res_tags.items() if v}

        missing_for_res = []
        for tag in req_tags:
            if tag.lower() in lower_tags and lower_tags[tag.lower()]:
                allocated_slots += 1
            else:
                missing_for_res.append(tag)

        if not missing_for_res:
            compliant_count += 1
        else:
            unallocated_inr += res.inr_hour
            untagged_list.append({
                "resource_id": res.resource_id,
                "kind": res.kind,
                "region": res.region,
                "inr_hour": res.inr_hour,
                "missing_tags": missing_for_res,
            })

    score_pct = round((allocated_slots / total_tag_slots) * 100.0, 1)

    if score_pct >= 90.0:
        grade = "A"
    elif score_pct >= 75.0:
        grade = "B"
    elif score_pct >= 60.0:
        grade = "C"
    else:
        grade = "F"

    return {
        "score_pct": score_pct,
        "grade": grade,
        "compliant_count": compliant_count,
        "total_resources": total_resources,
        "unallocated_inr_hour": round(unallocated_inr, 2),
        "untagged_resources": untagged_list,
        "required_tags": req_tags,
    }


def evaluate_budget_compliance(
    current_burn_inr: float,
    monthly_budget_inr: Optional[float] = None,
) -> Dict[str, Any]:
    """Evaluate burn rate against monthly budget ceiling in INR."""
    budget = monthly_budget_inr if monthly_budget_inr is not None else float(
        os.getenv("NETRA_MONTHLY_BUDGET_INR", "10000.0")
    )
    burn = max(0.0, float(current_burn_inr))
    projected_monthly = round(burn * 730.0, 2)
    variance_inr = round(projected_monthly - budget, 2)
    utilization_pct = round((projected_monthly / budget) * 100.0, 1) if budget > 0 else 100.0

    if projected_monthly > budget:
        status = "BREACHED"
        recommendation = "Immediate remediation needed: runaway spend exceeds monthly budget ceiling."
    elif projected_monthly >= (budget * 0.8):
        status = "WARNING"
        recommendation = "Approaching budget ceiling: review non-essential or idle test instances."
    else:
        status = "HEALTHY"
        recommendation = "Spend velocity is healthy and well within allocated monthly budget."

    days_until_exhausted = (
        round(budget / (burn * 24.0), 1) if burn > 0 else 999.0
    )

    return {
        "status": status,
        "monthly_budget_inr": budget,
        "current_burn_inr_hour": round(burn, 2),
        "projected_monthly_spend_inr": projected_monthly,
        "budget_variance_inr": variance_inr,
        "utilization_pct": utilization_pct,
        "days_until_budget_exhausted": days_until_exhausted,
        "recommendation": recommendation,
    }
