"""Unit tests for NETRA Cedar Policy Engine.

Verifies that policy/netra.cedar evaluates correctly, that all 5 safety rules
are enforced, and that forbid unconditionally beats permit by construction.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from netra.models import PricedResource
from netra.policy import check, explain, PolicyDecision, HAS_CEDARPY


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def test_cedar_policy_file_exists(repo_root):
    """Verify policy/netra.cedar and policy/entities.json exist."""
    cedar_file = repo_root / "policy" / "netra.cedar"
    entities_file = repo_root / "policy" / "entities.json"
    assert cedar_file.exists(), "policy/netra.cedar missing"
    assert entities_file.exists(), "policy/entities.json missing"
    assert "forbid_protected" in cedar_file.read_text(encoding="utf-8")


def test_cedarpy_is_available():
    """Verify cedarpy library is available for native policy evaluation."""
    assert HAS_CEDARPY is True, "cedarpy must be installed for native Cedar execution"


def test_cedar_forbid_protected():
    """Verify any action on netra:protected resource is forbidden."""
    res = PricedResource(
        resource_id="i-0protected123",
        kind="ec2",
        sub_type="t3.micro",
        region="ap-south-1",
        launched_at=1789740000,
        age_seconds=1200,
        usd_hour=0.0104,
        inr_hour=0.92,
        price_ref="sha256:ref",
        tags={"netra:protected": "true", "Owner": "alice"},
        state="running",
    )

    dec = check("stop", res, {"dependent_count": 0, "has_snapshot_step": True})
    assert dec.allowed is False
    assert dec.rule_id == "forbid_protected"
    assert "netra:protected" in explain(dec)


def test_cedar_forbid_dependents():
    """Verify terminate is forbidden when active dependents exist."""
    res = PricedResource(
        resource_id="i-0dependents123",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1789740000,
        age_seconds=3600,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="sha256:ref",
        tags={"Owner": "bob"},
        state="running",
    )

    dec = check("terminate", res, {"dependent_count": 2, "has_snapshot_step": True})
    assert dec.allowed is False
    assert dec.rule_id == "forbid_dependents"
    assert "active dependents" in explain(dec)


def test_cedar_forbid_unsnapshotted():
    """Verify bare termination is forbidden without an explicit snapshot step."""
    res = PricedResource(
        resource_id="i-0unsnapshotted123",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1789740000,
        age_seconds=3600,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="sha256:ref",
        tags={"Owner": "bob"},
        state="running",
    )

    dec = check("terminate", res, {"dependent_count": 0, "has_snapshot_step": False})
    assert dec.allowed is False
    assert dec.rule_id == "forbid_unsnapshotted"


def test_cedar_permit_owner_destructive():
    """Verify destructive action is permitted when owner is present and snapshot exists."""
    res = PricedResource(
        resource_id="i-0cleantoact123",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1789740000,
        age_seconds=3600,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="sha256:ref",
        tags={"Owner": "sre-lead"},
        state="running",
    )

    dec = check("terminate", res, {"dependent_count": 0, "has_snapshot_step": True})
    assert dec.allowed is True
    assert "permit" in dec.rule_id


def test_cedar_forbid_unconditionally_beats_permit():
    """Verify that a forbid policy unconditionally beats an overlapping permit rule."""
    # Resource has Owner="alice" (which matches permit_owner) BUT also netra:protected="true"
    res = PricedResource(
        resource_id="i-0conflict123",
        kind="ec2",
        sub_type="t3.micro",
        region="ap-south-1",
        launched_at=1789740000,
        age_seconds=1200,
        usd_hour=0.0104,
        inr_hour=0.92,
        price_ref="sha256:ref",
        tags={"Owner": "alice", "netra:protected": "true"},
        state="running",
    )

    # Even though permit_owner matches 'stop', forbid_protected MUST override it
    dec = check("stop", res)
    assert dec.allowed is False
    assert dec.rule_id == "forbid_protected"
