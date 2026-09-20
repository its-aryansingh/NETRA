"""Unit tests for netra.notify (critical SNS alerting)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest

from netra.models import Finding, Narrative, PricedResource
from netra.notify import publish_critical


@pytest.fixture
def sample_finding():
    res = PricedResource(
        resource_id="i-0a4f39c7b12e8d5a1",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1700000000,
        age_seconds=2460,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="sha256:abc",
        tags={},
        state="running",
        meta={},
    )
    narrative = Narrative(
        headline="Runaway c5.4xlarge burning 3.9x baseline",
        narrative=["Idle instance running for 41 minutes."],
        evidence=[{"label": "CPUUtilization", "value": "2.0%"}],
        recommended_action="snapshot_and_terminate",
        risk="medium",
        steps=[{"api": "ec2:TerminateInstances", "why": "terminate"}],
    )
    return Finding(
        finding_id="01J8ABCDEF1234567890123456",
        severity="critical",
        status="AWAITING_APPROVAL",
        rules_fired=[{"rule": "idle_compute", "detail": "cpu_max=2.0"}],
        resource=res,
        computed={
            "inr_hour": 66.55,
            "inr_month": 48576.0,
            "baseline_inr_hour": 23.04,
            "multiple": 3.89,
            "runway_hours": 14.9,
            "share_of_burn_pct": 94.4,
        },
        detected_at=1700002460,
        narrative=narrative,
    )


def test_publish_critical_no_topic_arn(monkeypatch, sample_finding):
    """Returns False safely when no topic ARN is configured."""
    monkeypatch.delenv("NETRA_ALERT_TOPIC_ARN", raising=False)
    monkeypatch.delenv("SNS_TOPIC_ARN", raising=False)
    monkeypatch.delenv("NETRA_SNS_TOPIC_ARN", raising=False)

    success = publish_critical(sample_finding)
    assert success is False


def test_publish_critical_success(monkeypatch, sample_finding):
    """Publishes correct subject and body within strict character limits."""
    topic_arn = "arn:aws:sns:ap-south-1:123456789012:netra-critical-findings-test"
    monkeypatch.setenv("NETRA_ALERT_TOPIC_ARN", topic_arn)
    monkeypatch.setenv("NETRA_DASHBOARD_URL", "https://netra.bharatbuilds.dev")

    mock_sns = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_sns

    success = publish_critical(sample_finding, session=mock_session)
    assert success is True
    assert mock_sns.publish.called

    call_kwargs = mock_sns.publish.call_args[1]
    assert call_kwargs["TopicArn"] == topic_arn

    subject = call_kwargs["Subject"]
    body = call_kwargs["Message"]

    assert len(subject) < 100
    assert len(body) < 300
    assert "NETRA: Rs 66.55/hr — c5.4xlarge i-0a4f39c7b12e8d5a1" in subject
    assert "Runaway c5.4xlarge burning 3.9x baseline" in body
    assert "Rs 48,576/month if it keeps running." in body
    assert "Credits gone in 14.9h." in body
    assert "https://netra.bharatbuilds.dev/investigations/01J8ABCDEF1234567890123456" in body


def test_publish_critical_strict_character_boundaries(monkeypatch, sample_finding):
    """Verifies that excessively long headlines/IDs do not breach 100/300 char limits."""
    monkeypatch.setenv("NETRA_ALERT_TOPIC_ARN", "arn:aws:sns:ap-south-1:123:test")
    monkeypatch.setenv("NETRA_DASHBOARD_URL", "https://extremely-long-subdomain-dashboard-url.bharatbuilds.dev")

    # Long headline and resource ID
    long_narrative = Narrative(
        headline="A" * 250,
        narrative=["test"],
        evidence=[],
        recommended_action="stop",
        risk="low",
        steps=[],
    )

    mock_sns = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_sns

    success = publish_critical(sample_finding, narrative=long_narrative, session=mock_session)
    assert success is True

    call_kwargs = mock_sns.publish.call_args[1]
    subject = call_kwargs["Subject"]
    body = call_kwargs["Message"]

    assert len(subject) < 100
    assert len(body) < 300


def test_publish_critical_never_raises(monkeypatch, sample_finding):
    """Publishes fails gracefully without raising on AWS client errors."""
    monkeypatch.setenv("NETRA_ALERT_TOPIC_ARN", "arn:aws:sns:ap-south-1:123:test")

    mock_sns = MagicMock()
    mock_sns.publish.side_effect = RuntimeError("AWS SNS service unavailable")
    mock_session = MagicMock()
    mock_session.client.return_value = mock_sns

    success = publish_critical(sample_finding, session=mock_session)
    assert success is False
