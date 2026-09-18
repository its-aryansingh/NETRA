"""Unit tests for NETRA collector Lambda.

Verifies end-to-end inventory collection, CloudWatch batch metrics query,
DynamoDB snapshot persistence, and EventBridge event emission.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from netra.collector import (
    _emit_finding_event,
    _get_cloudwatch_metrics_batch,
    _get_recent_baseline_totals,
    _save_finding,
    _save_snapshot,
    run_collector,
)
from netra.models import Finding, PricedResource


@pytest.fixture
def sample_resource() -> PricedResource:
    return PricedResource(
        resource_id="i-0testinstance123",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1789740000,
        age_seconds=2400,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="sha256:testref123",
        tags={"Owner": None, "netra:protected": None},
        state="running",
        meta={"vpc_id": "vpc-001"},
    )


def test_cloudwatch_metrics_batch(sample_resource):
    """Verify single batch query generates EC2 metric queries and extracts max CPU and packets."""
    mock_cw = MagicMock()
    mock_cw.get_metric_data.return_value = {
        "MetricDataResults": [
            {"Id": "m_cpu_0", "Values": [1.2, 2.0, 1.8]},
            {"Id": "m_net_0", "Values": [200.0, 300.0]},
        ]
    }

    metrics = _get_cloudwatch_metrics_batch(
        cloudwatch_client=mock_cw,
        resources=[sample_resource],
        now_epoch=1789740918,
    )

    mock_cw.get_metric_data.assert_called_once()
    assert sample_resource.resource_id in metrics
    res_m = metrics[sample_resource.resource_id]
    assert res_m["cpu_max_pct"] == 2.0
    assert res_m["network_packets_out"] == 500


def test_save_snapshot(sample_resource):
    """Verify snapshot item structure and TTL calculation."""
    mock_dynamo = MagicMock()
    _save_snapshot(
        dynamodb_client=mock_dynamo,
        resources=[sample_resource],
        now_epoch=1789740000,
        account_id="test_acc",
    )

    mock_dynamo.put_item.assert_called_once()
    call_args = mock_dynamo.put_item.call_args[1]
    item = call_args["Item"]
    assert item["pk"]["S"] == "ACCOUNT#test_acc"
    assert item["sk"]["S"] == "TS#1789740000"
    assert item["total_inr_hour"]["N"] == "66.55"
    assert item["ttl"]["N"] == str(1789740000 + 7 * 86400)


def test_emit_finding_event(sample_resource):
    """Verify EventBridge event emission format."""
    mock_events = MagicMock()
    finding = Finding(
        finding_id="01J8TESTFINDINGID123456",
        severity="critical",
        status="DETECTED",
        rules_fired=[{"rule": "idle_compute", "detail": "cpu_max=2.0"}],
        resource=sample_resource,
        computed={"inr_hour": 66.55},
        detected_at=1789740918,
    )

    _emit_finding_event(mock_events, finding)
    mock_events.put_events.assert_called_once()
    entries = mock_events.put_events.call_args[1]["Entries"]
    assert len(entries) == 1
    assert entries[0]["Source"] == "netra.collector"
    assert entries[0]["DetailType"] == "netra.finding.created"
    detail = json.loads(entries[0]["Detail"])
    assert detail["finding_id"] == "01J8TESTFINDINGID123456"


@patch("netra.collector.collect")
def test_run_collector_end_to_end(mock_collect, sample_resource):
    """Test entire collector execution cycle with mock session."""
    mock_collect.return_value = [sample_resource]

    mock_dynamo = MagicMock()
    # Baseline query
    mock_dynamo.query.return_value = {"Items": []}
    mock_cw = MagicMock()
    mock_cw.get_metric_data.return_value = {
        "MetricDataResults": [
            {"Id": "m_cpu_0", "Values": [1.5]},
            {"Id": "m_net_0", "Values": [100.0]},
        ]
    }
    mock_events = MagicMock()

    mock_session = MagicMock()
    def mock_client_factory(service_name, **kwargs):
        if service_name == "dynamodb":
            return mock_dynamo
        if service_name == "cloudwatch":
            return mock_cw
        if service_name == "events":
            return mock_events
        return MagicMock()

    mock_session.client.side_effect = mock_client_factory

    result = run_collector(session=mock_session)

    assert result["status"] == "ok"
    assert result["total_inr_hour"] == 66.55
    assert result["resources_count"] == 1
    assert result["new_findings_count"] >= 1
    mock_events.put_events.assert_called_once()
