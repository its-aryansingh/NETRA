"""Tests for NETRA Enterprise Extensions.

Verifies:
- Multi-Region fleet inventory collection and regional breakdown.
- Slack Block Kit payload generation and webhook dispatcher.
- Predictive spend forecasting, acceleration math, and P10/P50/P90 bands.
- Automated rollback state machine, snapshot validation, and restoration.
- FinOps tag compliance scoring and budget threshold evaluation.
- AWS Organizations AssumeRole fleet scanning and account discovery.
- Chaos test scenario execution and invariant verification.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from netra.models import Finding, PricedResource
from netra.inventory import collect, by_region
from netra.notifications import build_slack_blocks, dispatch_slack_alert, dispatch_webhook, dispatch_external_alerts
from netra.forecast import calculate_burn_acceleration, project_monthly_spend
from netra.executor import rollback_restore
from netra.mcp.tools import netra_rollback
from netra.budget import calculate_tag_governance_score, evaluate_budget_compliance
from netra.cross_account import assume_fleet_role, get_organization_accounts
from netra.collector import run_fleet_collector

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.chaos import run_chaos_suite


# ==============================================================================
# 1. Multi-Region Scanning Tests
# ==============================================================================

def test_by_region_aggregation():
    """Verify by_region calculates total inr_hour grouped by AWS region."""
    r1 = PricedResource(
        resource_id="i-south",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1000,
        age_seconds=100,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="ref:1",
        tags={"Owner": "dev"},
        state="running",
    )
    r2 = PricedResource(
        resource_id="i-east",
        kind="ec2",
        sub_type="t3.micro",
        region="us-east-1",
        launched_at=1000,
        age_seconds=100,
        usd_hour=0.0104,
        inr_hour=0.92,
        price_ref="ref:2",
        tags={"Owner": "dev"},
        state="running",
    )
    r3 = PricedResource(
        resource_id="vol-south",
        kind="ebs",
        sub_type="gp3",
        region="ap-south-1",
        launched_at=1000,
        age_seconds=100,
        usd_hour=0.0125,
        inr_hour=1.11,
        price_ref="ref:3",
        tags={"Owner": "dev"},
        state="available",
    )

    breakdown = by_region([r1, r2, r3])
    assert breakdown["ap-south-1"] == round(66.55 + 1.11, 2)
    assert breakdown["us-east-1"] == 0.92


def test_multi_region_collection_concurrency():
    """Verify collect() with multiple regions queries each region and aggregates results."""
    def mock_single(session, reg, dynamo, pricing):
        return [
            PricedResource(
                resource_id=f"res-{reg}",
                kind="ec2",
                sub_type="t3.micro",
                region=reg,
                launched_at=1000,
                age_seconds=100,
                usd_hour=0.01,
                inr_hour=0.88,
                price_ref=f"ref:{reg}",
                tags={"Owner": "test"},
                state="running",
            )
        ]

    with patch("netra.inventory.collect_single_region", side_effect=mock_single):
        regions = ["ap-south-1", "us-east-1", "eu-west-1"]
        results = collect(regions=regions)
        assert len(results) == 3
        found_regions = {r.region for r in results}
        assert found_regions == set(regions)


# ==============================================================================
# 2. Slack & Webhook Dispatcher Tests
# ==============================================================================

def test_slack_block_kit_payload():
    """Verify Slack Block Kit structure contains required headers, metrics, and action buttons."""
    res = PricedResource(
        resource_id="i-slack-test",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1000,
        age_seconds=100,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="ref:slack",
        tags={"Owner": "finops"},
        state="running",
    )
    finding = Finding(
        finding_id="01J8TESTSLACK0000000001",
        severity="critical",
        status="AWAITING_APPROVAL",
        rules_fired=[{"rule": "idle_compute", "detail": "cpu=2%"}],
        resource=res,
        computed={"inr_hour": 66.55, "runway_hours": 14.9},
        detected_at=1789740918,
    )

    payload = build_slack_blocks(finding, inr_hour=66.55, runway_hours=14.9, cockpit_url="https://netra.dev")
    assert "blocks" in payload
    blocks = payload["blocks"]
    assert any(b.get("type") == "header" for b in blocks)
    assert any(b.get("type") == "actions" for b in blocks)
    # Check button URL
    action_block = next(b for b in blocks if b.get("type") == "actions")
    buttons = action_block.get("elements", [])
    assert any("https://netra.dev/findings/01J8TESTSLACK0000000001" in btn.get("url", "") for btn in buttons)


def test_dispatch_webhook_graceful_on_error():
    """Verify dispatch_webhook handles network errors gracefully without throwing."""
    ok = dispatch_webhook("http://invalid-test-domain-123456789.test", {"data": 123}, timeout=1)
    assert ok is False


# ==============================================================================
# 3. Predictive Spend Forecasting Tests
# ==============================================================================

def test_burn_acceleration_computation():
    """Verify second-derivative spend acceleration math across accelerating points."""
    # Point 1: 10 INR/hr at T=0
    # Point 2: 20 INR/hr at T=3600 (v1 = 10/hr)
    # Point 3: 40 INR/hr at T=7200 (v2 = 20/hr -> a = 10/hr^2)
    snapshots = [
        {"created_at": 0, "total_inr_hour": 10.0},
        {"created_at": 3600, "total_inr_hour": 20.0},
        {"created_at": 7200, "total_inr_hour": 40.0},
    ]
    res = calculate_burn_acceleration(snapshots)
    assert res["trend"] == "accelerating"
    assert res["acceleration_inr_hour_sq"] > 0.0
    assert res["samples"] == 3


def test_project_monthly_spend_confidence_intervals():
    """Verify 30-day projection intervals satisfy P10 <= P50 <= P90."""
    snapshots = [
        {"total_inr_hour": 50.0},
        {"total_inr_hour": 60.0},
        {"total_inr_hour": 70.0},
    ]
    proj = project_monthly_spend(snapshots=snapshots, current_burn_inr=66.55, confidence=0.9)
    assert proj["p50_inr_month"] == round(66.55 * 730, 2)
    assert proj["p10_inr_month"] <= proj["p50_inr_month"]
    assert proj["p50_inr_month"] <= proj["p90_inr_month"]
    assert proj["potential_savings_30d"] > 0.0


# ==============================================================================
# 4. Automated Rollback State Machine Tests
# ==============================================================================

def test_rollback_restore_success():
    """Verify rollback_restore validates snapshot, creates restored volume, and records audit."""
    mock_session = MagicMock()
    mock_ec2 = MagicMock()
    mock_session.client.return_value = mock_ec2
    mock_ec2.describe_snapshots.return_value = {
        "Snapshots": [{"SnapshotId": "snap-safeguard-001", "State": "completed"}]
    }
    mock_ec2.create_volume.return_value = {"VolumeId": "vol-restored-999"}

    with patch("netra.executor.load_finding") as mock_finding, \
         patch("netra.executor.record_audit_entry") as mock_audit, \
         patch("netra.executor.update_finding_status") as mock_update:

        mock_finding.return_value = {
            "finding_id": "01TESTFINDING01",
            "resource": {"resource_id": "vol-old-123", "kind": "ebs"},
        }
        mock_audit.return_value = {"audit_id": "AUD#123"}

        res = rollback_restore(
            finding_id="01TESTFINDING01",
            snapshot_id="snap-safeguard-001",
            session=mock_session,
        )

        assert res["success"] is True
        assert res["status"] == "ROLLED_BACK"
        assert res["restored_resource_id"] == "vol-restored-999"
        mock_ec2.create_volume.assert_called_once()
        mock_audit.assert_called_once()


def test_mcp_netra_rollback_tool():
    """Verify netra_rollback tool calls restoration across MCP boundary."""
    with patch("netra.executor.rollback_restore") as mock_restore:
        mock_restore.return_value = {
            "success": True,
            "status": "ROLLED_BACK",
            "restored_resource_id": "vol-restored-111",
        }
        resp = netra_rollback(audit_id="AUD#1789740000#01TESTFINDING01", snapshot_id="snap-123")
        assert resp["ok"] is True
        assert resp["action"] == "rollback"
        assert resp["status"] == "ROLLED_BACK"


# ==============================================================================
# 5. FinOps Tag & Budget Governance Tests
# ==============================================================================

def test_calculate_tag_governance_score():
    """Verify tag governance score calculation and untagged inventory detection."""
    r_compliant = PricedResource(
        resource_id="i-compliant",
        kind="ec2",
        sub_type="t3.micro",
        region="ap-south-1",
        launched_at=1000,
        age_seconds=100,
        usd_hour=0.01,
        inr_hour=0.88,
        price_ref="ref:1",
        tags={"Owner": "devops", "Environment": "production", "CostCenter": "CC-101"},
        state="running",
    )
    r_non_compliant = PricedResource(
        resource_id="i-non-compliant",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1000,
        age_seconds=100,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="ref:2",
        tags={"Owner": None},
        state="running",
    )

    report = calculate_tag_governance_score([r_compliant, r_non_compliant])
    assert report["total_resources"] == 2
    assert report["compliant_count"] == 1
    assert report["unallocated_inr_hour"] == 66.55
    assert len(report["untagged_resources"]) == 1
    assert report["untagged_resources"][0]["resource_id"] == "i-non-compliant"


def test_evaluate_budget_compliance_thresholds():
    """Verify budget evaluation status changes between HEALTHY, WARNING, and BREACHED."""
    # 1 INR/hr -> 730 INR/mo vs 10000 budget -> HEALTHY
    h_res = evaluate_budget_compliance(current_burn_inr=1.0, monthly_budget_inr=10000.0)
    assert h_res["status"] == "HEALTHY"

    # 12 INR/hr -> 8760 INR/mo vs 10000 budget (>= 80%) -> WARNING
    w_res = evaluate_budget_compliance(current_burn_inr=12.0, monthly_budget_inr=10000.0)
    assert w_res["status"] == "WARNING"

    # 66.55 INR/hr -> 48581.50 INR/mo vs 10000 budget (> 100%) -> BREACHED
    b_res = evaluate_budget_compliance(current_burn_inr=66.55, monthly_budget_inr=10000.0)
    assert b_res["status"] == "BREACHED"
    assert b_res["budget_variance_inr"] > 0.0


# ==============================================================================
# 6. AWS Organizations Cross-Account Scanning Tests
# ==============================================================================

def test_assume_fleet_role_offline_fallback():
    """Verify assume_fleet_role falls back gracefully when STS credentials unavailable."""
    sess = assume_fleet_role("123456789012")
    assert sess is not None


def test_get_organization_accounts_config():
    """Verify get_organization_accounts reads from NETRA_ORGANIZATION_ACCOUNTS env var."""
    with patch.dict("os.environ", {"NETRA_ORGANIZATION_ACCOUNTS": "111111111111,222222222222"}):
        accounts = get_organization_accounts()
        assert len(accounts) == 2
        assert accounts[0]["Id"] == "111111111111"
        assert accounts[1]["Id"] == "222222222222"


def test_run_fleet_collector():
    """Verify fleet collector iterates over accounts and compiles fleet total."""
    with patch("netra.cross_account.get_organization_accounts") as mock_accs, \
         patch("netra.collector.run_collector") as mock_col:

        mock_accs.return_value = [
            {"Id": "111", "Name": "Prod"},
            {"Id": "222", "Name": "Dev"},
        ]
        mock_col.return_value = {
            "status": "ok",
            "total_inr_hour": 50.0,
            "resources_count": 2,
        }

        fleet_res = run_fleet_collector()
        assert fleet_res["status"] == "ok"
        assert fleet_res["accounts_scanned"] == 2
        assert fleet_res["fleet_total_inr_hour"] == 100.0


# ==============================================================================
# 7. Automated Chaos & Synthetic Load Suite Tests
# ==============================================================================

def test_chaos_simulation_suite_passes():
    """Verify complete chaos suite passes all 5 resilience stages."""
    all_ok = run_chaos_suite()
    assert all_ok is True


# ==============================================================================
# 8. API Endpoint Routing & Handling Tests for New Routes
# ==============================================================================

def test_api_get_forecast():
    """Verify GET /api/forecast returns 200 with forecast and acceleration payloads."""
    from netra.api import lambda_handler
    event = {
        "rawPath": "/api/forecast",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["ok"] is True
    assert "forecast" in body
    assert "acceleration" in body


def test_api_get_governance():
    """Verify GET /api/governance returns 200 with budget and tag governance reports."""
    from netra.api import lambda_handler
    event = {
        "rawPath": "/api/governance",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["ok"] is True
    assert "budget" in body
    assert "tag_governance" in body


def test_api_get_accounts():
    """Verify GET /api/accounts returns 200 with member account list."""
    from netra.api import lambda_handler
    event = {
        "rawPath": "/api/accounts",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["ok"] is True
    assert "accounts" in body
    assert isinstance(body["accounts"], list)


def test_api_post_test_webhook():
    """Verify POST /api/alerts/test-webhook dispatches test payload."""
    from netra.api import lambda_handler
    event = {
        "rawPath": "/api/alerts/test-webhook",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"webhook_url": "http://127.0.0.1:9999/dummy", "type": "generic"}),
    }
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["ok"] is True
    assert "status" in body


def test_api_post_audit_rollback():
    """Verify POST /api/audit/{id}/rollback executes rollback handler."""
    from netra.api import lambda_handler
    event = {
        "rawPath": "/api/audit/AUD_123/rollback",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"snapshot_id": "snap-test-safeguard"}),
    }
    with patch("netra.executor.rollback_restore") as mock_restore:
        mock_restore.return_value = {
            "success": True,
            "status": "ROLLED_BACK",
            "finding_id": "AUD_123",
            "snapshot_id": "snap-test-safeguard",
        }
        resp = lambda_handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["status"] == "ROLLED_BACK"
