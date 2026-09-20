"""Unit tests for NETRA event plumbing and notification architecture.

Verifies CloudWatch custom metrics, SQS batch processing with DLQ partial failures,
SNS mobile push alerting (<300 characters), and the $200 credit basis.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from netra.agent.investigator import (
    _publish_critical_alert,
    lambda_handler,
)
from netra.config import CREDITS_INITIAL_USD, CREDITS_REMAINING_USD
from netra.metrics import put_metric
from netra.models import Finding, Narrative, PricedResource


@pytest.fixture
def sample_finding() -> Finding:
    res = PricedResource(
        resource_id="i-0a4f39c7b12345678",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1789740000,
        age_seconds=2400,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="sha256:ref",
        tags={"Owner": None},
        state="running",
    )
    return Finding(
        finding_id="fnd-plumbing-01",
        resource=res,
        severity="critical",
        status="DETECTED",
        rules_fired=[{"rule": "idle_runaway_ec2", "detail": "c5.4xlarge idle 40m"}],
        computed={
            "inr_hour": 66.55,
            "inr_month": 48581.5,
            "baseline_inr_hour": 12.0,
            "multiple": 5.5,
            "runway_hours": 14.9,
            "share_of_burn_pct": 82.5,
        },
        detected_at=1789742400,
        narrative=Narrative(
            headline="Unattached c5.4xlarge compute burning ₹66.55/hr",
            narrative=["Idle compute instance without active workload."],
            evidence=[{"label": "CPU", "value": "0.8%"}],
            recommended_action="Stop instance to protect credits",
            risk="low",
            steps=[{"api": "ec2:StopInstances", "why": "Immediate burn halt"}],
        ),
    )


# ----------------------------------------------------------------------
# 1. CloudWatch Metrics Tests
# ----------------------------------------------------------------------

def test_put_metric_success():
    """Verify put_metric emits to NETRA namespace with expected schema."""
    mock_cw = MagicMock()
    mock_sess = MagicMock()
    mock_sess.client.return_value = mock_cw

    success = put_metric(
        name="BurnRateINRPerHour",
        value=127.30,
        unit="None",
        dimensions={"Region": "ap-south-1"},
        session=mock_sess,
    )

    assert success is True
    mock_cw.put_metric_data.assert_called_once_with(
        Namespace="NETRA",
        MetricData=[
            {
                "MetricName": "BurnRateINRPerHour",
                "Value": 127.30,
                "Unit": "None",
                "Dimensions": [{"Name": "Region", "Value": "ap-south-1"}],
            }
        ],
    )


def test_put_metric_suppresses_exceptions():
    """Verify put_metric never raises when CloudWatch fails."""
    mock_sess = MagicMock()
    mock_sess.client.side_effect = RuntimeError("CloudWatch service unavailable")

    success = put_metric(
        name="DetectionLatencyMs",
        value=420.0,
        unit="Milliseconds",
        session=mock_sess,
    )

    # Must fail softly without raising
    assert success is False


# ----------------------------------------------------------------------
# 2. SQS Batch & DLQ Partial Failure Tests
# ----------------------------------------------------------------------

@patch("netra.agent.investigator.investigate_finding")
def test_investigator_sqs_batch_processing(mock_investigate, sample_finding):
    """Verify SQS batch is unwrapped and processed successfully."""
    mock_investigate.return_value = sample_finding

    sqs_event = {
        "Records": [
            {
                "messageId": "msg-001",
                "body": json.dumps({
                    "detail": sample_finding.to_dict()
                }),
            },
            {
                "messageId": "msg-002",
                "body": json.dumps(sample_finding.to_dict()),
            },
        ]
    }

    resp = lambda_handler(sqs_event)
    assert resp["statusCode"] == 200
    assert len(resp["processed"]) == 2
    assert resp["batchItemFailures"] == []
    assert mock_investigate.call_count == 2


@patch("netra.agent.investigator.investigate_finding")
def test_investigator_sqs_partial_batch_failure(mock_investigate, sample_finding):
    """Verify corrupt record reports batchItemFailures for SQS redrive to DLQ."""
    mock_investigate.return_value = sample_finding

    sqs_event = {
        "Records": [
            {
                "messageId": "msg-good",
                "body": json.dumps(sample_finding.to_dict()),
            },
            {
                "messageId": "msg-bad",
                "body": "INVALID_JSON_CORRUPT_PAYLOAD",
            },
        ]
    }

    resp = lambda_handler(sqs_event)
    assert resp["statusCode"] == 200
    assert "fnd-plumbing-01" in resp["processed"]
    assert resp["batchItemFailures"] == [{"itemIdentifier": "msg-bad"}]


@patch("netra.agent.investigator.investigate_finding")
def test_investigator_direct_eventbridge_invocation(mock_investigate, sample_finding):
    """Verify direct EventBridge event format remains backward compatible."""
    mock_investigate.return_value = sample_finding

    event = {"detail": sample_finding.to_dict()}
    resp = lambda_handler(event)

    assert resp["statusCode"] == 200
    assert resp["finding_id"] == sample_finding.finding_id


# ----------------------------------------------------------------------
# 3. SNS Mobile Alerting Tests
# ----------------------------------------------------------------------

def test_publish_critical_alert_formatting_and_length(sample_finding):
    """Verify SNS alert payload is concise (<300 chars) for mobile notification."""
    mock_sns = MagicMock()
    mock_sess = MagicMock()
    mock_sess.client.return_value = mock_sns

    with patch("netra.config.SNS_TOPIC_ARN", "arn:aws:sns:ap-south-1:123456789012:netra-critical-findings"):
        success = _publish_critical_alert(sample_finding, session=mock_sess)

    assert success is True
    mock_sns.publish.assert_called_once()
    call_kwargs = mock_sns.publish.call_args[1]

    subject = call_kwargs["Subject"]
    message = call_kwargs["Message"]

    assert subject.startswith("NETRA:")
    assert sample_finding.resource.resource_id in subject
    assert len(message) < 300
    assert f"https://netra.dev/investigations/{sample_finding.finding_id}" in message
    assert "Runway:" in message


def test_publish_critical_alert_no_topic_graceful(sample_finding):
    """Verify _publish_critical_alert safely returns False when no SNS topic is set."""
    with patch("netra.config.SNS_TOPIC_ARN", ""):
        with patch.dict("os.environ", {"NETRA_SNS_TOPIC_ARN": ""}):
            success = _publish_critical_alert(sample_finding)
            assert success is False


# ----------------------------------------------------------------------
# 4. $200 Credit Basis Fix Tests
# ----------------------------------------------------------------------

def test_credit_basis_config():
    """Verify default initial and remaining credits equal $200.00."""
    assert CREDITS_INITIAL_USD == 200.0
    assert CREDITS_REMAINING_USD == 200.0


def test_api_summary_returns_200_basis():
    """Verify api.handle_summary exposes credits_initial_usd = 200.0."""
    from netra.api import handle_summary

    mock_db = MagicMock()
    # Mock empty query for snapshots
    mock_db.query.return_value = {"Items": []}
    mock_sess = MagicMock()
    mock_sess.client.return_value = mock_db

    resp = handle_summary({}, session=mock_sess)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body.get("credits_initial_usd") == 200.0
