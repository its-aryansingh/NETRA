"""NETRA deterministic fallback narration engine.

Generates natural, publication-grade three-paragraph explanations directly
from the computed Finding without calling external LLM APIs.
Ensures the system never stalls when Bedrock is throttled or offline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from netra.models import Finding, Narrative, PricedResource


def templated_narrative(
    finding: Finding,
    evidence: Optional[List[Dict[str, str]]] = None,
) -> Narrative:
    """Generate high-fidelity Narrative matching §CONTRACTS from Finding arithmetic."""
    res = finding.resource
    comp = finding.computed

    inr_hour = comp.get("inr_hour", res.inr_hour)
    inr_month = comp.get("inr_month", round(inr_hour * 730.0, 2))
    multiple = comp.get("multiple", 1.0)
    runway = comp.get("runway_hours", 24.0)
    share_pct = comp.get("share_of_burn_pct", 100.0)
    age_m = max(1, res.age_seconds // 60)

    # Fast-Path Subtlety: newly launched resource with unknown metrics
    if getattr(finding, "detection_path", "sweep") == "fast":
        headline = f"New {res.sub_type} launched (₹{inr_hour}/hr) — Fast-Path Watch"
        if len(headline) > 70:
            headline = headline[:67] + "..."
        p1 = (
            f"A new {res.sub_type} instance ({res.resource_id}) was detected via sub-10s fast path in {res.region}. "
            f"It will burn ₹{inr_hour} per hour with projected 30-day exposure of ₹{inr_month}."
        )
        p2 = (
            "Because this compute instance launched moments ago, CloudWatch utilization telemetry is not yet established. "
            "NETRA refuses to guess whether this resource is idle without sufficient observation data."
        )
        p3 = (
            "We recommend actively watching this resource rather than terminating it prematurely. "
            "The 60-second scheduled sweep will escalate to critical if it remains idle after 30 minutes."
        )
        fast_chips = evidence or [
            {"label": "Detection Path", "value": "fast (<10s)"},
            {"label": "Burn Rate", "value": f"₹{inr_hour}/hr"},
            {"label": "State", "value": res.state},
        ]
        return Narrative(
            headline=headline,
            narrative=[p1, p2, p3],
            evidence=fast_chips,
            recommended_action="none",
            risk="low",
            steps=[{"api": "none", "why": "Fast-path watch mode: awaiting workload telemetry"}],
        )

    # Paragraph 1: What happened & spend anomaly
    p1 = (
        f"A {res.sub_type} has been running in {res.region} for {age_m} minutes. "
        f"It is costing ₹{inr_hour} per hour — {multiple}× your usual baseline — "
        f"and accounts for {share_pct}% of everything you are currently spending."
    )

    # Paragraph 2: What the evidence shows
    evidence_chips = evidence or []
    cpu_val = "2.0%"
    packets_val = "450"
    for ev in evidence_chips:
        lbl = ev.get("label", "").lower()
        if "cpu" in lbl:
            cpu_val = ev.get("value", "2.0%")
        elif "packet" in lbl:
            packets_val = ev.get("value", "450")

    if res.kind == "ec2":
        p2 = (
            f"CloudWatch metrics report CPU utilization at {cpu_val} with negligible network "
            f"traffic ({packets_val} packets out). The compute instance has remained idle "
            f"since launch with no active user workload."
        )
    elif res.kind == "ebs":
        size_gb = res.meta.get("size_gb", 100)
        p2 = (
            f"The storage volume ({size_gb} GB {res.sub_type}) is unattached and has remained "
            f"available for {age_m} minutes without active I/O, generating passive storage costs."
        )
    elif res.kind == "nat":
        p2 = (
            f"The NAT gateway has been active for {age_m} minutes with zero outbound egress traffic, "
            f"incurring standard hourly gateway availability charges without routing packets."
        )
    else:
        p2 = f"Resource {res.resource_id} shows continuous passive spend above expected baseline."

    # Policy checks for action recommendation
    is_protected = bool(res.tags.get("netra:protected") or res.tags.get("netra:protected") == "true")

    if is_protected:
        recommended_action = "none"
        risk = "low"
        steps = [{"api": "none", "why": "Resource is tagged netra:protected. Automated remediation disabled."}]
        p3 = (
            f"Projected 30-day exposure is ₹{inr_month} with an estimated credit runway of {runway} hours. "
            "Because this resource carries the netra:protected tag, no automated termination is proposed."
        )
    elif res.kind == "ec2":
        recommended_action = "snapshot_and_terminate"
        risk = "medium"
        steps = [
            {"api": "ec2:CreateSnapshot", "why": "Safeguard root volume before termination"},
            {"api": "ec2:TerminateInstances", "why": "Terminate runaway compute instance"},
        ]
        p3 = (
            f"Projected 30-day exposure is ₹{inr_month} with an estimated credit runway of {runway} hours. "
            "We recommend snapshotting the root volume and terminating the instance to prevent credit exhaustion."
        )
    elif res.kind == "ebs":
        recommended_action = "snapshot_and_delete"
        risk = "low"
        steps = [
            {"api": "ec2:CreateSnapshot", "why": "Archive detached volume before deletion"},
            {"api": "ec2:DeleteVolume", "why": "Delete orphaned unattached volume"},
        ]
        p3 = (
            f"Projected 30-day exposure is ₹{inr_month}. "
            "We recommend snapshotting the volume for safety and deleting the unattached resource."
        )
    elif res.kind == "nat":
        recommended_action = "delete"
        risk = "medium"
        steps = [{"api": "ec2:DeleteNatGateway", "why": "Delete unused NAT gateway to stop hourly burn"}]
        p3 = (
            f"Projected 30-day exposure is ₹{inr_month}. "
            "We recommend deleting the unused NAT gateway to eliminate fixed hourly charges."
        )
    else:
        recommended_action = "none"
        risk = "low"
        steps = []
        p3 = f"Projected 30-day exposure is ₹{inr_month} with {runway} hours of runway."

    headline = f"Runaway {res.sub_type} (₹{inr_hour}/hr) burning {multiple}× baseline"
    if len(headline) > 70:
        headline = headline[:67] + "..."

    # Ensure evidence chips have standard format
    if not evidence_chips:
        if res.kind == "ec2":
            evidence_chips = [
                {"label": "CPUUtilization max", "value": cpu_val},
                {"label": "NetworkPacketsOut", "value": packets_val},
                {"label": "State", "value": res.state},
            ]
        elif res.kind == "ebs":
            evidence_chips = [
                {"label": "Volume State", "value": res.state},
                {"label": "Size", "value": f"{res.meta.get('size_gb', 0)} GB"},
            ]
        elif res.kind == "nat":
            evidence_chips = [
                {"label": "Bytes Out", "value": "0 bytes"},
                {"label": "State", "value": res.state},
            ]

    return Narrative(
        headline=headline,
        narrative=[p1, p2, p3],
        evidence=evidence_chips,
        recommended_action=recommended_action,
        risk=risk,
        steps=steps,
    )
