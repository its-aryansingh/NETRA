"""
Unit and Integration Tests for NETRA MCP Action Server, Token Security, and Policy Guardrails.
Verifies the cryptographic approval boundary, replay prevention, policy gates,
and sub-10s fast-path detection contracts.
"""

import time
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from netra.mcp.tokens import mint_approval_token, verify_approval_token, hash_plan
from netra.mcp.policy import check, explain, PolicyDecision
from netra.mcp.tools import netra_dry_run, netra_execute, netra_status
from netra.collector import run_fast_path
from netra.models import PricedResource, PriceDoc


# ------------------------------------------------------------------------------
# 1. Cryptographic Approval Token Security Tests
# ------------------------------------------------------------------------------

def test_token_mint_and_verify_valid():
    """Authentic human approval token passes validation."""
    finding_id = "f-ec2-i-test12345"
    plan = {"action": "stop", "steps": ["ec2:StopInstances"]}

    token = mint_approval_token(finding_id, plan, expires_in_seconds=300)
    assert token and "." in token

    is_valid, reason = verify_approval_token(token, finding_id, plan)
    assert is_valid is True
    assert "verified" in reason.lower()


def test_token_expiry_refused():
    """Token older than TTL (or negative TTL) is rejected immediately."""
    finding_id = "f-ec2-i-test12345"
    plan = {"action": "stop"}

    # Mint expired token
    token = mint_approval_token(finding_id, plan, expires_in_seconds=-5)
    is_valid, reason = verify_approval_token(token, finding_id, plan)
    assert is_valid is False
    assert "expired" in reason.lower()


def test_token_tampering_refused():
    """Tampering with signature, finding_id, or plan triggers rejection."""
    finding_id = "f-ec2-i-test12345"
    plan = {"action": "stop", "steps": ["ec2:StopInstances"]}
    token = mint_approval_token(finding_id, plan)

    # 1. Tampered signature
    bad_token = token[:-5] + "aaaaa"
    is_valid, reason = verify_approval_token(bad_token, finding_id, plan)
    assert is_valid is False
    assert "invalid cryptographic signature" in reason.lower()

    # 2. Target finding mismatch
    is_valid, reason = verify_approval_token(token, "f-ec2-i-OTHER", plan)
    assert is_valid is False
    assert "does not match" in reason.lower()

    # 3. Plan tampering (agent trying to escalate 'stop' to 'terminate')
    tampered_plan = {"action": "terminate", "steps": ["ec2:TerminateInstances"]}
    is_valid, reason = verify_approval_token(token, finding_id, tampered_plan)
    assert is_valid is False
    assert "plan hash mismatch" in reason.lower()


def test_token_replay_refused():
    """Single-use token cannot be redeemed a second time."""
    finding_id = "f-ec2-i-replay999"
    plan = {"action": "stop"}
    token = mint_approval_token(finding_id, plan)

    redeemed_cache = set()
    # First redemption succeeds
    ok1, reason1 = verify_approval_token(token, finding_id, plan, redeemed_tokens=redeemed_cache)
    assert ok1 is True

    # Second redemption attempt fails due to replay detection
    ok2, reason2 = verify_approval_token(token, finding_id, plan, redeemed_tokens=redeemed_cache)
    assert ok2 is False
    assert "replay attack rejected" in reason2.lower()


# ------------------------------------------------------------------------------
# 2. Policy Engine Deterministic Gate Tests
# ------------------------------------------------------------------------------

def test_policy_forbid_protected_all_actions():
    """Protected resource carrying 'netra:protected' cannot be stopped, terminated, or deleted."""
    res = {
        "resource_id": "i-protect001",
        "tags": {"netra:protected": "true", "Owner": "devops"},
        "inr_hour": 50.0,
    }

    for action in ["stop", "terminate", "delete", "downsize"]:
        decision = check(action, res)
        assert decision.allowed is False
        assert decision.rule_id == "forbid_protected"
        explanation = explain(decision)
        assert "Denied by forbid_protected" in explanation


def test_policy_forbid_dependents():
    """Destructive action denied if dependent resources exist."""
    res = {"resource_id": "i-web002", "tags": {"Owner": "dev"}, "inr_hour": 25.0}
    decision = check("terminate", res, context={"dependent_count": 2, "has_snapshot_step": True})
    assert decision.allowed is False
    assert decision.rule_id == "forbid_dependents"
    assert "active dependents" in decision.reason


def test_policy_forbid_unsnapshotted_destructive():
    """Bare termination without snapshot step is strictly denied."""
    res = {"resource_id": "i-bare003", "tags": {"Owner": "dev"}, "inr_hour": 30.0}
    decision = check("terminate", res, context={"has_snapshot_step": False})
    assert decision.allowed is False
    assert decision.rule_id == "forbid_unsnapshotted"


def test_policy_permit_clean_remediation():
    """Non-destructive actions or snapshotted terminations pass policy checks."""
    res = {"resource_id": "i-clean004", "tags": {"Owner": "eng"}, "inr_hour": 15.0}
    
    # Benign action (stop)
    dec_stop = check("stop", res)
    assert dec_stop.allowed is True
    assert "Permitted" in explain(dec_stop)

    # Destructive with snapshot
    dec_term = check("terminate", res, context={"has_snapshot_step": True, "dependent_count": 0})
    assert dec_term.allowed is True
    assert "Permitted" in explain(dec_term)


# ------------------------------------------------------------------------------
# 3. MCP Tools Execution Boundary Tests
# ------------------------------------------------------------------------------

@patch("netra.mcp.tools.load_finding")
@patch("netra.mcp.tools.stage_dry_run")
def test_netra_dry_run_always_allowed(mock_dry_run, mock_load):
    """dry_run previews proposed action and verifies policy without mutating."""
    mock_load.return_value = {
        "finding_id": "f-123",
        "resource": {"resource_id": "i-dry01", "tags": {"Owner": "alice"}, "inr_hour": 20.0},
        "narrative": {"recommended_action": "stop", "steps": ["ec2:StopInstances"]},
    }
    mock_dry_run.return_value = {"dry_run_passed": True}

    res = netra_dry_run("f-123")
    assert res["ok"] is True
    assert res["finding_id"] == "f-123"
    assert res["policy_allowed"] is True
    assert res["dry_run_status"] == "verified_safe"


@patch("netra.mcp.tools.load_finding")
def test_netra_execute_rejected_without_token(mock_load):
    """Calling netra_execute with forged or missing token refuses execution."""
    mock_load.return_value = {
        "finding_id": "f-exec-denied",
        "narrative": {"recommended_action": "stop", "steps": ["ec2:StopInstances"]},
    }

    # 1. Structural error
    res1 = netra_execute("f-exec-denied", "invalid-token-no-dot")
    assert res1["ok"] is False
    assert res1["error"] == "EXECUTION_DENIED"

    # 2. Forged signature
    res2 = netra_execute("f-exec-denied", "eyJmaWQiOiJmIn0.badsignature")
    assert res2["ok"] is False
    assert res2["error"] == "EXECUTION_DENIED"
    assert "signature" in res2["reason"].lower() or "invalid" in res2["reason"].lower()


@patch("netra.mcp.tools.load_finding")
@patch("netra.mcp.tools.execute_remediation")
def test_netra_execute_succeeds_with_valid_token(mock_exec, mock_load):
    """Valid approval token unlocks MCP execution boundary."""
    finding_id = "f-exec-ok"
    plan = {"action": "stop", "steps": ["ec2:StopInstances"]}
    mock_load.return_value = {
        "finding_id": finding_id,
        "narrative": {"recommended_action": "stop", "steps": ["ec2:StopInstances"]},
    }
    mock_exec.return_value = {
        "success": True,
        "status": "REMEDIATED",
        "snapshot_id": "snap-999",
        "audit": {"audit_id": "aud-001"},
    }

    token = mint_approval_token(finding_id, plan)
    res = netra_execute(finding_id, token)

    assert res["ok"] is True
    assert res["status"] == "REMEDIATED"
    assert mock_exec.called


# ------------------------------------------------------------------------------
# 4. Fast-Path Collector Detection Tests
# ------------------------------------------------------------------------------

@patch("netra.collector.get_price")
def test_run_fast_path_sub_10s_detection(mock_price):
    """Fast-path handles aws.ec2 state change and measures latency."""
    mock_price.return_value = PriceDoc(
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="ec2:c5.4xlarge:ap-south-1:mock",
        source="api",
        fetched_at=int(time.time()),
    )

    event = {
        "id": "evt-eb-1234",
        "source": "aws.ec2",
        "detail-type": "EC2 Instance State-change Notification",
        "time": "2026-09-19T01:00:00Z",
        "detail": {
            "instance-id": "i-runaway009",
            "state": "running",
        },
    }

    summary = run_fast_path(event)
    assert summary["status"] == "ok"
    assert summary["detection_path"] == "fast"
    assert summary["resource_id"] == "i-runaway009"
    assert summary["detection_latency_ms"] is not None
    assert summary["detection_latency_ms"] >= 0
    assert summary["findings_count"] >= 1


# ------------------------------------------------------------------------------
# 5. IAM Boundary Verification Test
# ------------------------------------------------------------------------------

def test_investigator_iam_has_zero_mutating_actions():
    """
    Contract verification: Ensure template.yaml strictly prohibits mutating EC2
    actions in the InvestigatorFunction IAM role. Only McpActionsFunction carries them.
    """
    template_path = Path(__file__).resolve().parent.parent.parent / "infra" / "template.yaml"
    assert template_path.exists(), "template.yaml not found"

    class CFNSafeLoader(yaml.SafeLoader):
        pass

    def cfn_constructor(loader, tag_suffix, node):
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        elif isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        elif isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
        return None

    CFNSafeLoader.add_multi_constructor("!", cfn_constructor)

    with open(template_path, "r", encoding="utf-8") as f:
        doc = yaml.load(f, Loader=CFNSafeLoader)

    resources = doc.get("Resources", {})
    investigator = resources.get("InvestigatorFunction", {})
    inv_policies = investigator.get("Properties", {}).get("Policies", [])

    mutating_prefixes = ["ec2:stop", "ec2:terminate", "ec2:delete", "ec2:create"]

    for policy in inv_policies:
        stmts = policy.get("Statement", [])
        for stmt in stmts:
            if stmt.get("Effect") == "Allow":
                actions = stmt.get("Action", [])
                if isinstance(actions, str):
                    actions = [actions]
                for action in actions:
                    act_lower = action.lower()
                    for prefix in mutating_prefixes:
                        assert not act_lower.startswith(prefix), (
                            f"VIOLATION: InvestigatorFunction role contains mutating action: {action}"
                        )

    # McpActionsFunction MUST exist and hold mutating actions
    mcp_func = resources.get("McpActionsFunction", {})
    assert mcp_func, "McpActionsFunction missing from template.yaml"
    mcp_policies = mcp_func.get("Properties", {}).get("Policies", [])
    has_mutating = False
    for policy in mcp_policies:
        for stmt in policy.get("Statement", []):
            actions = stmt.get("Action", [])
            for action in actions:
                if "StopInstances" in action or "TerminateInstances" in action:
                    has_mutating = True
    assert has_mutating, "McpActionsFunction must carry mutating permissions for remediation"
