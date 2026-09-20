"""
Unit tests for NETRA Cost Explorer integration.
Covers hourly resolution, daily fallback, error handling, staleness arithmetic, and caching.
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock
import pytest
from botocore.exceptions import ClientError

from netra.costexplorer import get_reported_burn


def test_hourly_success():
    """Verify hourly Cost Explorer resolution parses the latest positive non-zero period."""
    mock_ce = MagicMock()
    mock_ce.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-09-20T10:00:00Z", "End": "2026-09-20T11:00:00Z"},
                "Total": {"UnblendedCost": {"Amount": "0.2079", "Unit": "USD"}},
            },
            {
                "TimePeriod": {"Start": "2026-09-20T11:00:00Z", "End": "2026-09-20T12:00:00Z"},
                "Total": {"UnblendedCost": {"Amount": "0.0000", "Unit": "USD"}},
            },
        ]
    }
    result = get_reported_burn(ce_client=mock_ce, ddb_client=None)

    assert result["available"] is True
    assert result["granularity"] == "HOURLY"
    assert result["usd_hour"] == 0.2079
    assert result["inr_hour"] == round(0.2079 * 88.50, 2)
    assert result["reason"] is None
    assert result["staleness_seconds"] >= 0


def test_hourly_raises_then_daily_succeeds():
    """Verify daily fallback is engaged if hourly query encounters DataUnavailable."""
    mock_ce = MagicMock()

    # First call (hourly) raises DataUnavailableException
    error_response = {"Error": {"Code": "DataUnavailableException", "Message": "Hourly data not enabled"}}
    hourly_error = ClientError(error_response, "GetCostAndUsage")

    daily_success = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-09-18", "End": "2026-09-19"},
                "Total": {"UnblendedCost": {"Amount": "4.992", "Unit": "USD"}},
            }
        ]
    }

    mock_ce.get_cost_and_usage.side_effect = [hourly_error, daily_success]

    result = get_reported_burn(ce_client=mock_ce, ddb_client=None)

    assert result["available"] is True
    assert result["granularity"] == "DAILY"
    assert result["usd_hour"] == round(4.992 / 24.0, 4)
    assert result["inr_hour"] == round((4.992 / 24.0) * 88.50, 2)
    assert result["staleness_seconds"] >= 0


def test_data_unavailable_exception_not_enabled():
    """Verify DataUnavailableException across calls returns available=False with reason=not_enabled."""
    mock_ce = MagicMock()
    error_response = {"Error": {"Code": "DataUnavailableException", "Message": "Cost Explorer is not enabled"}}
    mock_ce.get_cost_and_usage.side_effect = ClientError(error_response, "GetCostAndUsage")

    result = get_reported_burn(ce_client=mock_ce, ddb_client=None)

    assert result["available"] is False
    assert result["reason"] == "not_enabled"
    assert result["inr_hour"] == 0.0


def test_all_zero_periods_no_data_yet():
    """Verify all periods reporting 0.00 return available=False with reason=no_data_yet."""
    mock_ce = MagicMock()
    mock_ce.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-09-20T10:00:00Z", "End": "2026-09-20T11:00:00Z"},
                "Total": {"UnblendedCost": {"Amount": "0.0000", "Unit": "USD"}},
            }
        ]
    }

    result = get_reported_burn(ce_client=mock_ce, ddb_client=None)

    assert result["available"] is False
    assert result["reason"] == "no_data_yet"


def test_staleness_arithmetic():
    """Verify staleness arithmetic calculates correct delta from period end."""
    now = datetime.datetime.now(datetime.timezone.utc)
    target_as_of = now - datetime.timedelta(hours=14)
    iso_end = target_as_of.strftime("%Y-%m-%dT%H:00:00Z")

    mock_ce = MagicMock()
    mock_ce.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-09-20T00:00:00Z", "End": iso_end},
                "Total": {"UnblendedCost": {"Amount": "0.2079", "Unit": "USD"}},
            }
        ]
    }

    result = get_reported_burn(ce_client=mock_ce, ddb_client=None)
    # Staleness should be approximately 14 hours (50400 seconds) within 1 hour rounding
    assert 48000 <= result["staleness_seconds"] <= 55000


def test_cache_hit_avoids_api_call():
    """Verify cache hit in DynamoDB price cache returns cached record without calling Cost Explorer API."""
    mock_ce = MagicMock()
    mock_ddb = MagicMock()

    future_ttl = int(datetime.datetime.now(datetime.timezone.utc).timestamp()) + 1200
    mock_ddb.get_item.return_value = {
        "Item": {
            "pk": {"S": "PRICE#reported#default"},
            "ttl": {"N": str(future_ttl)},
            "inr_hour": {"N": "18.40"},
            "usd_hour": {"N": "0.2079"},
            "as_of_epoch": {"N": "1726700000"},
            "granularity": {"S": "HOURLY"},
            "available": {"BOOL": True},
        }
    }

    result = get_reported_burn(ce_client=mock_ce, ddb_client=mock_ddb)

    # API should not be called
    mock_ce.get_cost_and_usage.assert_not_called()
    assert result["available"] is True
    assert result["inr_hour"] == 18.40
    assert result["usd_hour"] == 0.2079
