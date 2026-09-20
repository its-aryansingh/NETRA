"""Unit tests for NETRA HTTP API router.

Verifies:
1. All 12 API routes return documented JSON contract shapes.
2. CORS headers are returned on all endpoints including OPTIONS preflight.
3. Dynamic path extraction for findings approve, dismiss, snooze, and details.
4. Decimal-to-float conversions prevent JSON serialization exceptions.
5. 404 and 500 error shielding with structured JSON errors.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from netra.api import lambda_handler


@pytest.fixture
def mock_session():
    sess = MagicMock()
    mock_dynamo = MagicMock()
    mock_dynamo.query.return_value = {"Items": []}
    mock_dynamo.get_item.return_value = {}
    mock_dynamo.scan.return_value = {"Items": []}
    mock_dynamo.update_item.return_value = {}
    mock_dynamo.put_item.return_value = {}

    def client_factory(svc, **kwargs):
        if svc == "dynamodb":
            return mock_dynamo
        return MagicMock()

    sess.client.side_effect = client_factory
    return sess


def test_cors_options_preflight():
    """Verify OPTIONS request returns 200 with open CORS headers."""
    event = {
        "rawPath": "/api/summary",
        "requestContext": {"http": {"method": "OPTIONS"}},
    }
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200
    assert resp["headers"]["Access-Control-Allow-Origin"] == "*"


def test_get_summary(mock_session):
    """Verify GET /api/summary returns expected contract fields."""
    event = {
        "rawPath": "/api/summary",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "burn_inr_hour" in body
    assert "baseline_inr_hour" in body
    assert "multiple" in body
    assert "projected_month_inr" in body
    assert "credits_remaining_usd" in body
    assert "runway_hours" in body
    assert "usd_inr" in body
    assert "detection_latency_ms_p50" in body
    assert "detection_path_counts" in body
    assert body["usd_inr"] == 88.50


def test_get_burn(mock_session):
    """Verify GET /api/burn returns points series and baseline."""
    event = {
        "rawPath": "/api/burn",
        "requestContext": {"http": {"method": "GET"}},
        "queryStringParameters": {"hours": "12"},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "points" in body
    assert "baseline_inr_hour" in body


def test_get_inventory(mock_session):
    """Verify GET /api/inventory returns resources array and counts."""
    event = {
        "rawPath": "/api/inventory",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "resources" in body
    assert "counts" in body


def test_get_findings_list(mock_session):
    """Verify GET /api/findings returns findings array."""
    event = {
        "rawPath": "/api/findings",
        "requestContext": {"http": {"method": "GET"}},
        "queryStringParameters": {"status": "open"},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "findings" in body


def test_get_finding_detail(mock_session):
    """Verify GET /api/findings/{id} returns full finding record."""
    dynamo = mock_session.client("dynamodb")
    dynamo.get_item.return_value = {
        "Item": {
            "finding_id": {"S": "01J8TESTFINDINGID123"},
            "status": {"S": "AWAITING_APPROVAL"},
            "severity": {"S": "critical"},
            "detected_at": {"N": "1789740918"},
            "narrative_source": {"S": "fallback"},
            "narrative": {"S": json.dumps({"headline": "Runaway c5.4xlarge detected"})},
        }
    }

    event = {
        "rawPath": "/api/findings/01J8TESTFINDINGID123",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["finding_id"] == "01J8TESTFINDINGID123"
    assert body["status"] == "AWAITING_APPROVAL"


def test_post_finding_approve(mock_session):
    """Verify POST /api/findings/{id}/approve transitions status to EXECUTING."""
    event = {
        "rawPath": "/api/findings/01J8TESTFINDINGID123/approve",
        "requestContext": {"http": {"method": "POST"}},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "EXECUTING"
    assert "execution_arn" in body
    assert body.get("token_minted") is True


def test_post_finding_dismiss(mock_session):
    """Verify POST /api/findings/{id}/dismiss transitions status to DISMISSED."""
    event = {
        "rawPath": "/api/findings/01J8TESTFINDINGID123/dismiss",
        "requestContext": {"http": {"method": "POST"}},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "DISMISSED"


def test_post_finding_snooze(mock_session):
    """Verify POST /api/findings/{id}/snooze transitions status to SNOOZED with epoch time."""
    event = {
        "rawPath": "/api/findings/01J8TESTFINDINGID123/snooze",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"hours": 4}),
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "SNOOZED"
    assert "snoozed_until" in body


def test_get_audit(mock_session):
    """Verify GET /api/audit returns ledger and recovered metrics."""
    event = {
        "rawPath": "/api/audit",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "entries" in body
    assert "recovered_month_inr" in body


def test_get_audit_by_cause(mock_session):
    """Verify GET /api/audit/by-cause returns breakdown causes."""
    event = {
        "rawPath": "/api/audit/by-cause",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "causes" in body
    assert len(body["causes"]) >= 1


def test_get_verify(mock_session):
    """Verify GET /api/verify returns verification checks and status."""
    event = {
        "rawPath": "/api/verify",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "verified"
    assert "checks" in body


def test_post_demo_simulate(mock_session):
    """Verify POST /api/demo/simulate injects synthetic finding and returns finding_id."""
    event = {
        "rawPath": "/api/demo/simulate",
        "requestContext": {"http": {"method": "POST"}},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "simulated"
    assert "finding_id" in body


def test_404_not_found(mock_session):
    """Verify unknown path returns shaped 404 error."""
    event = {
        "rawPath": "/api/unknown-endpoint",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp = lambda_handler(event, None, session=mock_session)
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert body["code"] == "NOT_FOUND"
    assert resp["headers"]["Access-Control-Allow-Origin"] == "*"


def test_error_path_returns_cors_headers(mock_session, monkeypatch):
    """Verify 404 and 500 error paths return CORS headers to prevent browser CORS masking."""
    # 404 path
    event_404 = {
        "rawPath": "/api/unknown-endpoint",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp_404 = lambda_handler(event_404, None, session=mock_session)
    assert resp_404["statusCode"] == 404
    assert resp_404["headers"]["Access-Control-Allow-Origin"] == "*"
    assert "content-type" in resp_404["headers"]["Access-Control-Allow-Headers"].lower()
    assert "authorization" in resp_404["headers"]["Access-Control-Allow-Headers"].lower()

    # 500 path
    monkeypatch.setattr("netra.api.handle_summary", MagicMock(side_effect=RuntimeError("Handler crashed")))
    event_500 = {
        "rawPath": "/api/summary",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp_500 = lambda_handler(event_500, None, session=mock_session)
    assert resp_500["statusCode"] == 500
    assert resp_500["headers"]["Access-Control-Allow-Origin"] == "*"
    assert "content-type" in resp_500["headers"]["Access-Control-Allow-Headers"].lower()
    assert "authorization" in resp_500["headers"]["Access-Control-Allow-Headers"].lower()
    body_500 = json.loads(resp_500["body"])
    assert body_500["code"] == "INTERNAL_ERROR"


def test_extract_boto_session_from_headers():
    """Verify _extract_boto_session dynamically reads IAM headers."""
    from netra.api import _extract_boto_session
    event = {
        "headers": {
            "x-aws-access-key-id": "AKIAIOSFODNN7EXAMPLE",
            "x-aws-secret-access-key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "x-aws-region": "eu-west-1",
        }
    }
    sess = _extract_boto_session(event)
    assert sess.region_name == "eu-west-1"
    creds = sess.get_credentials()
    assert creds.access_key == "AKIAIOSFODNN7EXAMPLE"


