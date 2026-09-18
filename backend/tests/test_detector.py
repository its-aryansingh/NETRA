"""Tests for NETRA pure detector and rules-as-data engine.

Asserts exact Finding outputs from snapshot fixtures, verifies severity downgrades,
confirms deduplication, validates dynamic rules-as-data behavior, and proves
100% byte-identical determinism across multiple runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from netra.detector import evaluate, load_rules
from netra.models import Finding

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def test_step_change_detection():
    """Verify account-scope step change detection when spend exceeds 3x baseline and delta > 20."""
    fixture = _load_fixture("snapshot_step_change.json")
    findings = evaluate(
        snapshot=fixture["snapshot"],
        baseline_history=fixture["baseline_history"],
        detected_at=1789740918,
    )

    assert len(findings) >= 1
    # Finding attributed to the runaway c5.4xlarge
    c5_finding = next(f for f in findings if f.resource.sub_type == "c5.4xlarge")
    assert c5_finding.severity == "critical"

    fired_rule_ids = [r["rule"] for r in c5_finding.rules_fired]
    assert "burn_step_change" in fired_rule_ids

    # Computed block asserts
    assert c5_finding.computed["inr_hour"] == 66.55
    assert c5_finding.computed["baseline_inr_hour"] == 23.04
    assert c5_finding.computed["multiple"] > 3.0


def test_idle_compute_detection():
    """Verify idle compute detection for c5.4xlarge with low CPU utilization."""
    fixture = _load_fixture("snapshot_idle_compute.json")
    findings = evaluate(
        snapshot=fixture["snapshot"],
        baseline_history=fixture["baseline_history"],
        metrics=fixture["metrics"],
        detected_at=1789740918,
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.resource.resource_id == "i-0a4f39c7b12e8d5a1"
    assert finding.severity == "critical"

    fired_rule_ids = [r["rule"] for r in finding.rules_fired]
    assert "idle_compute" in fired_rule_ids
    assert finding.computed["share_of_burn_pct"] == 100.0


def test_idle_compute_severity_downgrade():
    """Verify idle compute downgrades from critical to warning when inr_hour < 50."""
    snapshot = {
        "total_inr_hour": 3.96,
        "resources": [
            {
                "resource_id": "i-0smallinstance123",
                "kind": "ec2",
                "sub_type": "t3.medium",
                "region": "ap-south-1",
                "launched_at": 1789730000,
                "age_seconds": 2400,
                "usd_hour": 0.0448,
                "inr_hour": 3.96,
                "price_ref": "fallback:t3.medium",
                "tags": {"Owner": "test", "netra:protected": None},
                "state": "running",
                "meta": {},
            }
        ],
    }
    metrics = {
        "i-0smallinstance123": {
            "cpu_max_pct": 1.2,
            "network_packets_out": 300,
        }
    }

    findings = evaluate(
        snapshot=snapshot,
        baseline_history=[3.96] * 12,
        metrics=metrics,
        detected_at=1789740918,
    )

    assert len(findings) == 1
    finding = findings[0]
    fired_rule_ids = [r["rule"] for r in finding.rules_fired]
    assert "idle_compute" in fired_rule_ids
    # Because inr_hour 3.96 < 50, severity should be downgraded to warning
    assert finding.severity == "warning"


def test_orphaned_storage_detection():
    """Verify orphaned EBS volume detection when status is available and age > 1 hour."""
    fixture = _load_fixture("snapshot_orphaned_storage.json")
    findings = evaluate(
        snapshot=fixture["snapshot"],
        baseline_history=fixture["baseline_history"],
        detected_at=1789740918,
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.resource.resource_id == "vol-0987654321fedcba0"
    assert finding.severity == "warning"

    fired_rule_ids = [r["rule"] for r in finding.rules_fired]
    assert "orphaned_storage" in fired_rule_ids


def test_idle_nat_gateway_detection():
    """Verify idle NAT gateway detection when bytes_out == 0 and age > 2 hours."""
    snapshot = {
        "total_inr_hour": 4.96,
        "resources": [
            {
                "resource_id": "nat-0idle000000000001",
                "kind": "nat",
                "sub_type": "nat",
                "region": "ap-south-1",
                "launched_at": 1789730000,
                "age_seconds": 8000,
                "usd_hour": 0.056,
                "inr_hour": 4.96,
                "price_ref": "fallback:nat",
                "tags": {"Owner": "infra", "netra:protected": None},
                "state": "available",
                "meta": {},
            }
        ],
    }
    metrics = {
        "nat-0idle000000000001": {
            "bytes_out": 0,
        }
    }

    findings = evaluate(
        snapshot=snapshot,
        baseline_history=[4.96] * 10,
        metrics=metrics,
        detected_at=1789740918,
    )

    assert len(findings) == 1
    finding = findings[0]
    assert "idle_nat" in [r["rule"] for r in finding.rules_fired]
    assert finding.severity == "warning"


def test_untagged_spend_detection():
    """Verify untagged spend detection when inr_hour > 5 and Owner tag is missing."""
    snapshot = {
        "total_inr_hour": 18.76,
        "resources": [
            {
                "resource_id": "i-0untagged00000001",
                "kind": "ec2",
                "sub_type": "m5.large",
                "region": "ap-south-1",
                "launched_at": 1789740000,
                "age_seconds": 600,
                "usd_hour": 0.106,
                "inr_hour": 9.38,
                "price_ref": "fallback:m5.large",
                "tags": {"Owner": None, "netra:protected": None},
                "state": "running",
                "meta": {},
            }
        ],
    }

    findings = evaluate(
        snapshot=snapshot,
        baseline_history=[18.76] * 10,
        detected_at=1789740918,
    )

    assert len(findings) == 1
    finding = findings[0]
    assert "untagged_spend" in [r["rule"] for r in finding.rules_fired]
    assert finding.severity == "info"


def test_protected_resource_detected():
    """Verify protected resource is still detected as an anomaly (policy prevents mutation in Phase 7)."""
    fixture = _load_fixture("snapshot_protected_resource.json")
    findings = evaluate(
        snapshot=fixture["snapshot"],
        baseline_history=fixture["baseline_history"],
        metrics=fixture["metrics"],
        detected_at=1789740918,
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.resource.resource_id == "i-0protected9999999"
    assert finding.resource.tags.get("netra:protected") == "true"
    assert "idle_compute" in [r["rule"] for r in finding.rules_fired]


def test_deduplication_open_findings():
    """Verify that resources with active findings are excluded from duplicate evaluation."""
    fixture = _load_fixture("snapshot_idle_compute.json")
    open_ids = {"i-0a4f39c7b12e8d5a1"}

    findings = evaluate(
        snapshot=fixture["snapshot"],
        baseline_history=fixture["baseline_history"],
        metrics=fixture["metrics"],
        open_finding_resource_ids=open_ids,
        detected_at=1789740918,
    )

    assert len(findings) == 0


def test_determinism():
    """Verify that evaluate is 100% pure and deterministic. Two runs produce byte-identical JSON output."""
    fixture = _load_fixture("snapshot_step_change.json")
    metrics = {
        "i-0a4f39c7b12e8d5a1": {
            "cpu_max_pct": 2.0,
            "network_packets_out": 450,
        }
    }

    findings_run1 = evaluate(
        snapshot=fixture["snapshot"],
        baseline_history=fixture["baseline_history"],
        metrics=metrics,
        detected_at=1789740918,
    )

    findings_run2 = evaluate(
        snapshot=fixture["snapshot"],
        baseline_history=fixture["baseline_history"],
        metrics=metrics,
        detected_at=1789740918,
    )

    json1 = json.dumps([f.to_dict() for f in findings_run1], sort_keys=True, indent=2)
    json2 = json.dumps([f.to_dict() for f in findings_run2], sort_keys=True, indent=2)

    assert json1 == json2
    assert findings_run1[0].finding_id == findings_run2[0].finding_id


def test_rules_as_data_dynamic_change():
    """Verify that adding a rule dynamically in data changes behavior with zero code edits."""
    custom_rules = {
        "rules": [
            {
                "id": "expensive_instance",
                "label": "Any instance costing above ₹50/hour",
                "severity": "critical",
                "scope": "resource",
                "all": [
                    {"field": "kind", "operator": "eq", "value": "ec2"},
                    {"field": "inr_hour", "operator": "gt", "value": 50.0},
                ],
            }
        ]
    }

    snapshot = {
        "total_inr_hour": 66.55,
        "resources": [
            {
                "resource_id": "i-0expensive123456",
                "kind": "ec2",
                "sub_type": "c5.4xlarge",
                "region": "ap-south-1",
                "launched_at": 1789740877,
                "age_seconds": 100,
                "usd_hour": 0.752,
                "inr_hour": 66.55,
                "price_ref": "fallback:c5.4xlarge",
                "tags": {"Owner": "demo", "netra:protected": None},
                "state": "running",
                "meta": {},
            }
        ],
    }

    findings = evaluate(
        snapshot=snapshot,
        baseline_history=[],
        rules=custom_rules,
        detected_at=1789740918,
    )

    assert len(findings) == 1
    assert findings[0].rules_fired[0]["rule"] == "expensive_instance"
