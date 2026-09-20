"""Unit tests for OpenAI GPT-4o mini integration in NETRA."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import urllib.error
import pytest

from netra.agent.investigator import (
    _invoke_llm,
    _invoke_openai,
    investigate_finding,
)
from netra.models import Finding, Narrative, PricedResource


@pytest.fixture
def mock_openai_response():
    narrative_payload = {
        "headline": "Runaway c5.4xlarge (Rs 66.55/hr) burning 2.89x baseline",
        "narrative": [
            "A c5.4xlarge compute instance has been running idle in ap-south-1 for 41 minutes.",
            "CloudWatch metrics report CPU utilization at 2.0% with negligible network traffic (450 packets out).",
            "Projected 30-day exposure is Rs 48576.0 with an estimated credit runway of 14.9 hours.",
        ],
        "evidence": [
            {"label": "CPUUtilization max", "value": "2.0%"},
            {"label": "NetworkPacketsOut", "value": "450"},
            {"label": "State", "value": "running"},
            {"label": "Active Dependents", "value": "0"},
        ],
        "recommended_action": "snapshot_and_terminate",
        "risk": "medium",
        "steps": [
            {"api": "ec2:CreateSnapshot", "why": "Safeguard root volume"},
            {"api": "ec2:TerminateInstances", "why": "Terminate idle instance"},
        ],
    }
    return {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(narrative_payload),
                },
                "finish_reason": "stop",
            }
        ],
    }


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
    return Finding(
        finding_id="01J8ABCDEF1234567890123456",
        severity="critical",
        status="DETECTED",
        rules_fired=[{"rule": "idle_compute", "detail": "cpu_max=2.0"}],
        resource=res,
        computed={
            "inr_hour": 66.55,
            "inr_month": 48576.0,
            "baseline_inr_hour": 23.04,
            "multiple": 2.89,
            "runway_hours": 14.9,
            "share_of_burn_pct": 74.0,
        },
        detected_at=1700002460,
    )


def test_invoke_openai_success(mock_openai_response):
    """Verifies that _invoke_openai correctly queries chat completions and parses JSON."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_openai_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        result = _invoke_openai(
            prompt="Analyze runaway spend",
            api_key="sk-test-secret-key",
            model="gpt-4o-mini",
        )

    assert result["headline"] == "Runaway c5.4xlarge (Rs 66.55/hr) burning 2.89x baseline"
    assert result["recommended_action"] == "snapshot_and_terminate"

    # Verify request payload and headers
    req_call = mock_urlopen.call_args[0][0]
    assert req_call.full_url == "https://api.openai.com/v1/chat/completions"
    assert req_call.headers["Authorization"] == "Bearer sk-test-secret-key"
    payload = json.loads(req_call.data.decode("utf-8"))
    assert payload["model"] == "gpt-4o-mini"
    assert payload["temperature"] == 0.0
    assert payload["response_format"] == {"type": "json_object"}


def test_invoke_openai_strips_markdown_code_fences(mock_openai_response):
    """Verifies that markdown fences in response are cleanly stripped."""
    content_raw = mock_openai_response["choices"][0]["message"]["content"]
    wrapped_content = f"```json\n{content_raw}\n```"
    mock_openai_response["choices"][0]["message"]["content"] = wrapped_content

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_openai_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = _invoke_openai(
            prompt="Analyze runaway spend",
            api_key="sk-test-secret-key",
        )

    assert result["headline"] == "Runaway c5.4xlarge (Rs 66.55/hr) burning 2.89x baseline"


def test_invoke_openai_missing_api_key(monkeypatch):
    """Verifies ValueError when OPENAI_API_KEY is not set."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is not configured"):
        _invoke_openai("prompt", api_key="")


def test_invoke_llm_routes_to_openai_by_default(monkeypatch, mock_openai_response):
    """Verifies _invoke_llm defaults to OpenAI."""
    monkeypatch.setenv("NETRA_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_openai_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = _invoke_llm("Analyze finding")

    assert "Runaway c5.4xlarge" in result["headline"]


def test_investigator_e2e_openai_success(monkeypatch, sample_finding, mock_openai_response):
    """End-to-end test: OpenAI generates narrative, passes validation, sets source to openai."""
    monkeypatch.setenv("NETRA_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_openai_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with patch("netra.agent.investigator.get_resource_details", return_value={"state": "running"}):
            with patch("netra.agent.investigator.get_cloudwatch_utilization", return_value={"cpu_utilization_max": 2.0, "network_packets_out": 450}):
                with patch("netra.agent.investigator.find_dependents", return_value={"count": 0}):
                    with patch("netra.agent.investigator._update_finding_status"):
                        updated = investigate_finding(sample_finding)

    assert updated.status == "AWAITING_APPROVAL"
    assert updated.narrative_source == "openai"
    assert updated.narrative is not None
    assert updated.narrative.recommended_action == "snapshot_and_terminate"


def test_investigator_openai_error_graceful_fallback(monkeypatch, sample_finding):
    """Verifies graceful fallback to deterministic narrative when OpenAI API fails."""
    monkeypatch.setenv("NETRA_MODEL_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with patch("netra.agent.investigator.get_resource_details", return_value={"state": "running"}):
        with patch("netra.agent.investigator.get_cloudwatch_utilization", return_value={"cpu_utilization_max": 2.0, "network_packets_out": 450}):
            with patch("netra.agent.investigator.find_dependents", return_value={"count": 0}):
                with patch("netra.agent.investigator._update_finding_status"):
                    updated = investigate_finding(sample_finding)

    assert updated.status == "AWAITING_APPROVAL"
    assert updated.narrative_source == "fallback"
    assert updated.narrative is not None
    assert "Runaway c5.4xlarge" in updated.narrative.headline
