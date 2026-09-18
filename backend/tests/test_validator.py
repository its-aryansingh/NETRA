"""Unit tests for NETRA agent numeric validator, fallback engine, and investigator.

Verifies:
1. Valid model narratives pass validation.
2. Hallucinated or untraceable numbers are rejected.
3. Terminating resources with active dependents is blocked.
4. Mutating protected resources is blocked.
5. Deterministic fallback narrative produces 100% valid, contract-compliant narratives.
6. Investigator automatically engages fallback when Bedrock is unavailable.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from netra.agent.fallback import templated_narrative
from netra.agent.investigator import investigate_finding
from netra.agent.validator import extract_numbers, validate
from netra.models import Finding, Narrative, PricedResource


@pytest.fixture
def sample_finding() -> Finding:
    res = PricedResource(
        resource_id="i-0a4f39c7b12e8d5a1",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1789740877,
        age_seconds=2460,  # 41 minutes
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="sha256:4a9f13c8",
        tags={"Owner": None, "netra:protected": None},
        state="running",
        meta={"vpc_id": "vpc-0a1b2c3d"},
    )
    return Finding(
        finding_id="01J8ABCDEF1234567890123456",
        severity="critical",
        status="DETECTED",
        rules_fired=[{"rule": "idle_compute", "detail": "cpu_max=2.0 age=41m"}],
        resource=res,
        computed={
            "inr_hour": 66.55,
            "inr_month": 48576.0,
            "baseline_inr_hour": 23.04,
            "multiple": 3.89,
            "runway_hours": 14.9,
            "share_of_burn_pct": 94.4,
        },
        detected_at=1789740918,
    )


@pytest.fixture
def sample_evidence() -> list[dict[str, str]]:
    return [
        {"label": "CPUUtilization max", "value": "2.0%"},
        {"label": "NetworkPacketsOut", "value": "450"},
        {"label": "State", "value": "running"},
        {"label": "Active Dependents", "value": "0"},
    ]


def test_extract_numbers():
    """Verify number extraction strips resource IDs and types while retaining currency and percentages."""
    text = "Instance i-0a4f39c7b12e8d5a1 (c5.4xlarge, gp3) has run for 41 minutes costing ₹66.55/hr (3.9x baseline)."
    nums = extract_numbers(text)
    assert 41.0 in nums
    assert 66.55 in nums
    assert 3.9 in nums


def test_valid_narrative_passes_validator(sample_finding, sample_evidence):
    """Verify that a compliant narrative referencing only computed and evidence numbers passes."""
    valid_narrative = Narrative(
        headline="Runaway c5.4xlarge (₹66.55/hr) burning 3.9× baseline",
        narrative=[
            "A c5.4xlarge has been running in ap-south-1 for 41 minutes. It is costing ₹66.55 per hour — 3.9× your usual baseline — and accounts for 94.4% of everything you are currently spending.",
            "CloudWatch metrics report CPU utilization at 2.0% with negligible network traffic (450 packets out). The compute instance has remained idle since launch with no active user workload.",
            "Projected 30-day exposure is ₹48576.0 with an estimated credit runway of 14.9 hours. We recommend snapshotting the root volume and terminating the instance.",
        ],
        evidence=sample_evidence,
        recommended_action="snapshot_and_terminate",
        risk="medium",
        steps=[
            {"api": "ec2:CreateSnapshot", "why": "Safeguard root volume before termination"},
            {"api": "ec2:TerminateInstances", "why": "Terminate runaway compute instance"},
        ],
    )

    is_valid, errors = validate(valid_narrative, sample_finding, sample_evidence, dependents_count=0)
    assert is_valid is True
    assert len(errors) == 0


def test_hallucinated_numbers_rejected(sample_finding, sample_evidence):
    """Verify validator strictly rejects narratives with hallucinated or untraceable numbers."""
    bad_narrative = Narrative(
        headline="Runaway c5.4xlarge (₹66.55/hr) burning 3.9× baseline",
        narrative=[
            "A c5.4xlarge has been running in ap-south-1 for 41 minutes costing ₹999.0 per hour.",  # 999.0 is hallucinated
            "CloudWatch metrics report CPU utilization at 2.0% with 450 packets out.",
            "Projected 30-day exposure is ₹48576.0 with 14.9 hours of runway.",
        ],
        evidence=sample_evidence,
        recommended_action="snapshot_and_terminate",
        risk="medium",
        steps=[],
    )

    is_valid, errors = validate(bad_narrative, sample_finding, sample_evidence)
    assert is_valid is False
    assert any("999" in err for err in errors)


def test_dependent_resource_termination_blocked(sample_finding, sample_evidence):
    """Verify that terminate/delete actions on resources with active dependents are rejected."""
    narrative = Narrative(
        headline="Runaway c5.4xlarge burning above baseline",
        narrative=[
            "A c5.4xlarge has been running for 41 minutes costing ₹66.55 per hour.",
            "CPU utilization is 2.0% with 450 packets out.",
            "Runway is 14.9 hours.",
        ],
        evidence=sample_evidence,
        recommended_action="terminate",
        risk="high",
        steps=[],
    )

    # With dependents_count = 2, terminate must be blocked
    is_valid, errors = validate(narrative, sample_finding, sample_evidence, dependents_count=2)
    assert is_valid is False
    assert any("active dependent" in err for err in errors)


def test_protected_resource_action_blocked(sample_evidence):
    """Verify that any remediation on resources tagged netra:protected is rejected."""
    protected_res = PricedResource(
        resource_id="i-0protected999",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1789740877,
        age_seconds=2460,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="sha256:protectedref",
        tags={"Owner": "lead", "netra:protected": "true"},
        state="running",
        meta={},
    )
    finding = Finding(
        finding_id="01J8PROTECTED1234567890123",
        severity="critical",
        status="DETECTED",
        rules_fired=[{"rule": "idle_compute", "detail": "cpu_max=2.0"}],
        resource=protected_res,
        computed={"inr_hour": 66.55, "runway_hours": 14.9},
        detected_at=1789740918,
    )

    narrative = Narrative(
        headline="Runaway c5.4xlarge burning above baseline",
        narrative=[
            "A c5.4xlarge has been running for 41 minutes costing ₹66.55 per hour.",
            "CPU utilization is 2.0% with 450 packets out.",
            "Runway is 14.9 hours.",
        ],
        evidence=sample_evidence,
        recommended_action="stop",  # Protected resources cannot have actions other than "none"
        risk="low",
        steps=[],
    )

    is_valid, errors = validate(narrative, finding, sample_evidence)
    assert is_valid is False
    assert any("netra:protected" in err for err in errors)


def test_templated_fallback_narrative_is_valid(sample_finding, sample_evidence):
    """Verify that templated_narrative produces a high quality narrative that passes validation with zero errors."""
    fallback_narrative = templated_narrative(sample_finding, sample_evidence)

    assert len(fallback_narrative.headline) <= 70
    assert len(fallback_narrative.narrative) == 3
    assert fallback_narrative.recommended_action == "snapshot_and_terminate"

    # Assert that all numbers in the generated fallback pass validation
    is_valid, errors = validate(fallback_narrative, sample_finding, sample_evidence, dependents_count=0)
    assert is_valid is True
    assert len(errors) == 0


@patch("netra.agent.investigator._invoke_llm")
def test_investigator_fallback_when_bedrock_fails(mock_llm, sample_finding):
    """Verify that investigator seamlessly falls back when Bedrock throttles or fails."""
    mock_llm.side_effect = Exception("ThrottlingException: Rate exceeded")

    mock_session = MagicMock()
    mock_session.client.return_value = MagicMock()

    result_finding = investigate_finding(sample_finding, session=mock_session)

    assert result_finding.status == "AWAITING_APPROVAL"
    assert result_finding.narrative_source == "fallback"
    assert result_finding.narrative is not None
    assert len(result_finding.narrative.narrative) == 3
    assert result_finding.agent_trace is not None
    assert len(result_finding.agent_trace) >= 1
