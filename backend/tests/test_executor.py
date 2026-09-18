"""
Tests for NETRA Remediation Policy Engine, Executor Pipeline, and System Verification.
Verifies safety gates, DryRun checks, snapshot safeguarding, audit logging,
and make verify execution.
"""

from unittest.mock import MagicMock, patch
import pytest
from botocore.exceptions import ClientError

from netra.models import PricedResource, Finding, Narrative
from netra.policy import check, explain
from netra.executor import (
    RemediationError,
    stage_authorize,
    stage_dry_run,
    stage_snapshot,
    stage_act,
    stage_record_audit,
    execute_remediation,
    lambda_handler,
)
from netra.verify import run_all_checks


@pytest.fixture
def mock_resource():
    return PricedResource(
        resource_id="i-0a4f39c7b12e8d5a1",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1789740877,
        age_seconds=2460,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="sha256:4a9f13c8...",
        tags={"Owner": "lead-dev", "netra:protected": None},
        state="running",
    )


@pytest.fixture
def mock_finding(mock_resource):
    return {
        "finding_id": "01J8TESTFINDING00000001",
        "severity": "critical",
        "status": "AWAITING_APPROVAL",
        "resource": mock_resource.to_dict(),
        "computed": {
            "inr_hour": 66.55,
            "inr_month": 48576.0,
            "baseline_inr_hour": 23.04,
            "multiple": 3.89,
            "runway_hours": 14.9,
            "share_of_burn_pct": 94.4,
        },
        "narrative": {
            "headline": "Runaway c5.4xlarge detected",
            "narrative": ["p1", "p2", "p3"],
            "recommended_action": "snapshot_and_terminate",
            "risk": "medium",
            "steps": [{"api": "ec2:CreateSnapshot", "why": "Safeguard volume"}],
        },
        "detected_at": 1789740918,
    }


# =========================================================================
# Policy Engine Tests
# =========================================================================

def test_policy_forbid_protected(mock_resource):
    protected_res = PricedResource(
        resource_id="i-0protected",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1789740877,
        age_seconds=2460,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="sha256:4a9f...",
        tags={"netra:protected": "true"},
        state="running",
    )
    decision = check("terminate", protected_res)
    assert not decision.allowed
    assert decision.rule_id == "forbid_protected"
    assert "netra:protected" in explain(decision)


def test_policy_forbid_dependents(mock_resource):
    # Destructive action with active dependents must be denied
    decision = check(
        action="terminate",
        resource=mock_resource,
        context={"dependent_count": 3},
    )
    assert not decision.allowed
    assert decision.rule_id == "forbid_dependents"


def test_policy_forbid_unsnapshotted(mock_resource):
    # Bare terminate without snapshot step must be denied
    decision = check(
        action="terminate",
        resource=mock_resource,
        context={"has_snapshot_step": False},
    )
    assert not decision.allowed
    assert decision.rule_id == "forbid_unsnapshotted"


def test_policy_permit_owner_non_destructive(mock_resource):
    decision = check(action="stop", resource=mock_resource)
    assert decision.allowed
    assert decision.rule_id == "permit_owner"


def test_policy_permit_owner_destructive_with_snapshot(mock_resource):
    decision = check(
        action="snapshot_and_terminate",
        resource=mock_resource,
        context={"has_snapshot_step": True},
    )
    assert decision.allowed
    assert "permit" in decision.rule_id


# =========================================================================
# Executor Pipeline Stage Tests
# =========================================================================

def test_stage_authorize_valid(mock_finding):
    session = MagicMock()
    res = stage_authorize(session, mock_finding, "snapshot_and_terminate")
    assert res["authorized"] is True
    assert res["action"] == "snapshot_and_terminate"


def test_stage_authorize_rejects_wrong_status(mock_finding):
    mock_finding["status"] = "RESOLVED"
    session = MagicMock()
    with pytest.raises(RemediationError, match="Cannot authorize"):
        stage_authorize(session, mock_finding, "snapshot_and_terminate")


def test_stage_authorize_rejects_deviating_action(mock_finding):
    session = MagicMock()
    with pytest.raises(RemediationError, match="deviates from approved plan"):
        stage_authorize(session, mock_finding, "stop")


def test_stage_dry_run_handles_dryrun_exception():
    session = MagicMock()
    ec2_mock = MagicMock()
    session.client.return_value = ec2_mock

    # DryRun=True in boto3 raises ClientError with Code="DryRunOperation"
    dry_run_error = ClientError(
        {"Error": {"Code": "DryRunOperation", "Message": "Request would have succeeded"}},
        "StopInstances",
    )
    ec2_mock.stop_instances.side_effect = dry_run_error

    res = stage_dry_run(session, {"resource_id": "i-123", "kind": "ec2"}, "stop")
    assert res["dry_run_passed"] is True


def test_stage_snapshot_creates_tagged_snapshot():
    session = MagicMock()
    ec2_mock = MagicMock()
    session.client.return_value = ec2_mock
    ec2_mock.describe_instances.return_value = {
        "Reservations": [
            {"Instances": [{"BlockDeviceMapping": [{"Ebs": {"VolumeId": "vol-root123"}}]}]}
        ]
    }
    ec2_mock.create_snapshot.return_value = {"SnapshotId": "snap-0123456789abcdef0"}

    snap_id = stage_snapshot(
        session,
        {"resource_id": "i-123", "kind": "ec2"},
        "snapshot_and_terminate",
        "01J8TEST",
    )
    assert snap_id == "snap-0123456789abcdef0"
    ec2_mock.create_snapshot.assert_called_once()


def test_stage_act_terminates_instance():
    session = MagicMock()
    ec2_mock = MagicMock()
    session.client.return_value = ec2_mock
    ec2_mock.terminate_instances.return_value = {"TerminatingInstances": []}

    res = stage_act(session, {"resource_id": "i-123", "kind": "ec2"}, "terminate")
    assert res["terminated"] is True
    ec2_mock.terminate_instances.assert_called_once_with(InstanceIds=["i-123"])


# =========================================================================
# End-to-End Execution & Verification Tests
# =========================================================================

@patch("netra.executor.load_finding")
@patch("netra.executor.update_finding_status")
@patch("netra.executor.record_audit_entry")
def test_execute_remediation_e2e_success(
    mock_audit,
    mock_update_status,
    mock_load_finding,
    mock_finding,
):
    mock_load_finding.return_value = mock_finding
    mock_audit.return_value = {"audit_id": "AUD#123#01J8", "ok": True}

    session = MagicMock()
    ec2_mock = MagicMock()
    session.client.return_value = ec2_mock

    # DryRun raises DryRunOperation (success)
    ec2_mock.terminate_instances.side_effect = [
        ClientError({"Error": {"Code": "DryRunOperation"}}, "TerminateInstances"),
        {"TerminatingInstances": []},
    ]
    ec2_mock.describe_instances.return_value = {
        "Reservations": [{"Instances": [{"BlockDeviceMapping": [{"Ebs": {"VolumeId": "vol-123"}}]}]}]
    }
    ec2_mock.create_snapshot.return_value = {"SnapshotId": "snap-rollback-123"}

    res = execute_remediation(
        session=session,
        finding_id="01J8TESTFINDING00000001",
        approved_action="snapshot_and_terminate",
        approved_by="test-engineer@netra.internal",
    )

    assert res["success"] is True
    assert res["status"] == "RESOLVED"
    assert res["snapshot_id"] == "snap-rollback-123"
    mock_update_status.assert_any_call(session, "01J8TESTFINDING00000001", "RESOLVED", "default")


def test_make_verify_all_checks_pass():
    """Validates that make verify runs in under 2 seconds and all 6 checks pass."""
    results = run_all_checks()
    assert results["all_passed"] is True
    assert results["status"] == "verified"
    assert len(results["checks"]) == 6
    assert results["duration_s"] < 2.0
    for c in results["checks"]:
        assert c["ok"] is True
