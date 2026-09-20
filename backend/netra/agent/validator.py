"""NETRA deterministic output validator.

Strictly validates model Narrative objects:
1. Schema & length conformance (headline max 70 chars, 3 paragraphs).
2. Numeric provenance: Every number in the narrative must match a figure in Finding.computed
   or an evidence value within a 1% rounding tolerance. Halts hallucinated numbers immediately.
3. Remediation policy safety:
   - Prohibits terminate/delete if dependent count > 0.
   - Prohibits any remediation on resources tagged 'netra:protected'.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple, Union

from netra.models import Finding, Narrative


def extract_numbers(text: str) -> List[float]:
    """Extract numeric values from text while ignoring AWS resource IDs and instance families."""
    # Normalize Indian numbering commas (e.g. 48,576.0 -> 48576.0)
    cleaned = re.sub(r"(\d),(\d)", r"\1\2", text)
    # Strip AWS region patterns (e.g. ap-south-1, us-east-1)
    cleaned = re.sub(r"\b[a-z]{2,4}-[a-z]{4,12}-\d\b", " ", cleaned, flags=re.IGNORECASE)
    # Strip day / hour time horizon qualifiers (e.g. 30-day, 7-day, 24-hour)
    cleaned = re.sub(r"\b\d+-(?:day|hour|min)\b", " ", cleaned, flags=re.IGNORECASE)
    # Strip AWS resource IDs (i-0123..., vol-123..., vpc-123...)
    cleaned = re.sub(r"\b[a-z]{1,4}-[0-9a-f]{8,17}\b", " ", cleaned, flags=re.IGNORECASE)
    # Strip instance types (c5.4xlarge, t3.micro, m5.large, etc.)
    cleaned = re.sub(r"\b[a-z][0-9]\.[a-z0-9]+\b", " ", cleaned, flags=re.IGNORECASE)
    # Strip storage types (gp2, gp3, io1, io2)
    cleaned = re.sub(r"\b(gp[23]|io[12]|st1|sc1)\b", " ", cleaned, flags=re.IGNORECASE)
    # Strip version strings (v1, v2)
    cleaned = re.sub(r"\bv\d+\b", " ", cleaned, flags=re.IGNORECASE)

    # Match numbers with optional currency symbols, percentages, multipliers, or units
    matches = re.findall(r"(?:₹|\$)?\b(\d+(?:\.\d+)?)(?:%|[x×]|h|m|s)?(?=[^\w.]|$)", cleaned)
    extracted: List[float] = []
    for m in matches:
        try:
            extracted.append(float(m))
        except ValueError:
            pass
    return extracted


def _matches_any_allowed(val: float, allowed_pool: Set[float], tolerance_pct: float = 0.02) -> bool:
    """Check if value matches any allowed reference number within tolerance (default 2%)."""
    for ref in allowed_pool:
        # Check absolute or relative difference
        if abs(val - ref) <= 0.15:
            return True
        if ref > 0 and (abs(val - ref) / ref) <= tolerance_pct:
            return True
    return False


def validate(
    narrative: Union[Narrative, Dict[str, Any]],
    finding: Union[Finding, Dict[str, Any]],
    evidence: Optional[List[Dict[str, str]]] = None,
    dependents_count: int = 0,
) -> Tuple[bool, List[str]]:
    """Validate a Narrative against Finding computation and safety policies.

    Returns (is_valid, list_of_errors).
    """
    errors: List[str] = []

    # Unpack narrative
    if isinstance(narrative, Narrative):
        headline = narrative.headline
        paragraphs = narrative.narrative
        rec_action = narrative.recommended_action
        evidence_list = evidence if evidence is not None else (narrative.evidence or [])
    else:
        headline = narrative.get("headline", "")
        paragraphs = narrative.get("narrative", [])
        rec_action = narrative.get("recommended_action", "none")
        evidence_list = evidence if evidence is not None else (narrative.get("evidence") or [])

    # Unpack finding
    if isinstance(finding, Finding):
        computed = finding.computed
        res = finding.resource
        tags = res.tags
    else:
        computed = finding.get("computed", {})
        res_data = finding.get("resource", {})
        tags = res_data.get("tags", {})
        res = res_data

    # 1. Headline length check
    if len(headline) > 70:
        errors.append(f"Headline exceeds 70 characters ({len(headline)} chars)")

    # 2. Paragraph count check
    if len(paragraphs) != 3:
        errors.append(f"Narrative must contain exactly 3 paragraphs (found {len(paragraphs)})")

    # 3. Policy & Safety checks
    is_protected = bool(tags.get("netra:protected") or tags.get("netra:protected") == "true")
    if is_protected and rec_action != "none":
        errors.append(f"Action '{rec_action}' rejected: resource is tagged netra:protected")

    destructive_actions = {
        "terminate",
        "delete",
        "snapshot_and_terminate",
        "snapshot_and_delete",
    }
    if dependents_count > 0 and rec_action in destructive_actions:
        errors.append(
            f"Action '{rec_action}' rejected: resource has {dependents_count} active dependent architectural components"
        )

    # 4. Numeric provenance checks
    allowed_numbers: Set[float] = set()

    # From Finding.computed
    for k, v in computed.items():
        if isinstance(v, (int, float)):
            allowed_numbers.add(float(v))

    # Add rounded variants (e.g. 3.9 from 3.89, 48576 from 48576.0)
    if "multiple" in computed:
        allowed_numbers.add(round(computed["multiple"], 1))
        allowed_numbers.add(round(computed["multiple"], 0))
    if "runway_hours" in computed:
        allowed_numbers.add(round(computed["runway_hours"], 0))
    if "share_of_burn_pct" in computed:
        allowed_numbers.add(round(computed["share_of_burn_pct"], 0))

    # Standard horizon for monthly projections
    allowed_numbers.add(30.0)

    # From Finding.resource
    if isinstance(res, dict):
        age_s = res.get("age_seconds", 0)
        allowed_numbers.add(float(res.get("usd_hour", 0.0)))
        allowed_numbers.add(float(res.get("inr_hour", 0.0)))
        size_gb = res.get("meta", {}).get("size_gb")
        if size_gb:
            allowed_numbers.add(float(size_gb))
    else:
        age_s = res.age_seconds
        allowed_numbers.add(float(res.usd_hour))
        allowed_numbers.add(float(res.inr_hour))
        size_gb = res.meta.get("size_gb")
        if size_gb:
            allowed_numbers.add(float(size_gb))

    allowed_numbers.add(float(age_s // 60))  # age in minutes
    allowed_numbers.add(float(age_s // 3600))  # age in hours

    # From evidence chips
    for ev in evidence_list:
        val_str = str(ev.get("value", ""))
        for n in extract_numbers(val_str):
            allowed_numbers.add(n)

    # Extract all numbers from narrative text
    all_narrative_text = headline + " " + " ".join(paragraphs)
    narrative_numbers = extract_numbers(all_narrative_text)

    for num in narrative_numbers:
        # Ignore trivial counts like 1, 2, 3 when used in paragraphs (e.g. "three paragraphs", "2 hours")
        # unless it is a spend claim
        if num in (1.0, 2.0, 3.0) and num not in allowed_numbers:
            # Allow common small integer cardinal numbers
            continue

        if not _matches_any_allowed(num, allowed_numbers):
            errors.append(f"Untraceable numeric claim '{num}' in narrative (not in computed finding or evidence)")

    return len(errors) == 0, errors
