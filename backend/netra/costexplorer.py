"""
NETRA AWS Cost Explorer Integration.
Queries what AWS itself believes the account is spending, measuring observability staleness.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import time
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from netra.config import REGION, TABLE_PRICE_CACHE, USD_INR, get_logger

logger = get_logger("netra.costexplorer")


def _iso_hour(dt: datetime.datetime) -> str:
    """Format datetime as YYYY-MM-DDTHH:00:00Z."""
    return dt.strftime("%Y-%m-%dT%H:00:00Z")


def _iso_day(dt: datetime.datetime) -> str:
    """Format datetime as YYYY-MM-DD."""
    return dt.strftime("%Y-%m-%d")


def get_reported_burn(
    ce_client: Optional[Any] = None,
    ddb_client: Optional[Any] = None,
    account_id: str = "default",
) -> Dict[str, Any]:
    """
    What AWS itself believes this account is spending, and how stale that belief is.
    Returns:
      {
        "inr_hour": float,
        "usd_hour": float,
        "as_of_epoch": int,
        "staleness_seconds": int,
        "granularity": str,  # "HOURLY" | "DAILY"
        "available": bool,
        "reason": Optional[str]  # "not_enabled" | "no_data_yet" | "error"
      }
    """
    now = datetime.datetime.now(timezone.utc)
    now_epoch = int(now.timestamp())

    # Check DynamoDB cache first (30m TTL)
    # Cost Explorer bills about $0.01 per paginated request — an uncached call behind a 5-second
    # dashboard poll would cost more than the waste this product detects.
    cache_key = f"PRICE#reported#{account_id}"
    if ddb_client:
        try:
            resp = ddb_client.get_item(
                TableName=TABLE_PRICE_CACHE,
                Key={"pk": {"S": cache_key}},
            )
            item = resp.get("Item")
            if item:
                ttl_val = int(item.get("ttl", {}).get("N", 0))
                if ttl_val > now_epoch:
                    as_of_epoch = int(item.get("as_of_epoch", {}).get("N", now_epoch))
                    usd_hour = float(item.get("usd_hour", {}).get("N", 0.0))
                    inr_hour = float(item.get("inr_hour", {}).get("N", 0.0))
                    avail = item.get("available", {}).get("BOOL", True)
                    granularity = item.get("granularity", {}).get("S", "HOURLY")
                    reason = item.get("reason", {}).get("S")
                    return {
                        "inr_hour": inr_hour,
                        "usd_hour": usd_hour,
                        "as_of_epoch": as_of_epoch,
                        "staleness_seconds": max(0, now_epoch - as_of_epoch),
                        "granularity": granularity,
                        "available": avail,
                        "reason": reason,
                    }
        except Exception as err:
            logger.warning(f"Cache check failed for reported cost: {err}")

    # Initialize Cost Explorer client in us-east-1 (global endpoint)
    client = ce_client
    if client is None:
        try:
            client = boto3.client("ce", region_name="us-east-1")
        except Exception as err:
            logger.warning(f"Failed to create Cost Explorer client: {err}")
            return {
                "inr_hour": 0.0,
                "usd_hour": 0.0,
                "as_of_epoch": now_epoch,
                "staleness_seconds": 0,
                "granularity": "HOURLY",
                "available": False,
                "reason": "error",
            }

    # 1. Attempt HOURLY resolution (last 48 hours)
    start_48h = now - datetime.timedelta(hours=48)
    try:
        resp = client.get_cost_and_usage(
            TimePeriod={"Start": _iso_hour(start_48h), "End": _iso_hour(now)},
            Granularity="HOURLY",
            Metrics=["UnblendedCost"],
        )
        results = resp.get("ResultsByTime", [])
        all_zero = True
        for period in reversed(results):
            cost_amount_str = period.get("Total", {}).get("UnblendedCost", {}).get("Amount", "0")
            try:
                amt = float(cost_amount_str)
            except (ValueError, TypeError):
                amt = 0.0

            if amt > 0:
                all_zero = False
                end_str = period.get("TimePeriod", {}).get("End")
                try:
                    end_dt = datetime.datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    as_of = int(end_dt.timestamp())
                except Exception:
                    as_of = now_epoch - 3600

                usd_hour = amt
                inr_hour = round(usd_hour * USD_INR, 2)
                result = {
                    "inr_hour": inr_hour,
                    "usd_hour": round(usd_hour, 4),
                    "as_of_epoch": as_of,
                    "staleness_seconds": max(0, now_epoch - as_of),
                    "granularity": "HOURLY",
                    "available": True,
                    "reason": None,
                }
                _write_cache(ddb_client, cache_key, result, now_epoch + 1800)
                return result

        if results and all_zero:
            # Fall through to daily if all zero or check daily
            pass
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if "DataUnavailable" in code:
            # Not enabled for hourly
            pass
        else:
            logger.warning(f"Hourly cost query failed with {code}: {exc}")
    except Exception as exc:
        logger.warning(f"Hourly cost query error: {exc}")

    # 2. Fallback to DAILY resolution (last 3 days)
    start_3d = now - datetime.timedelta(days=3)
    try:
        resp = client.get_cost_and_usage(
            TimePeriod={"Start": _iso_day(start_3d), "End": _iso_day(now)},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )
        results = resp.get("ResultsByTime", [])
        all_zero = True
        for period in reversed(results):
            cost_amount_str = period.get("Total", {}).get("UnblendedCost", {}).get("Amount", "0")
            try:
                amt = float(cost_amount_str)
            except (ValueError, TypeError):
                amt = 0.0

            if amt > 0:
                all_zero = False
                end_str = period.get("TimePeriod", {}).get("End")
                try:
                    end_dt = datetime.datetime.fromisoformat(end_str + "T00:00:00+00:00")
                    as_of = int(end_dt.timestamp())
                except Exception:
                    as_of = now_epoch - 86400

                usd_hour = amt / 24.0
                inr_hour = round(usd_hour * USD_INR, 2)
                result = {
                    "inr_hour": inr_hour,
                    "usd_hour": round(usd_hour, 4),
                    "as_of_epoch": as_of,
                    "staleness_seconds": max(0, now_epoch - as_of),
                    "granularity": "DAILY",
                    "available": True,
                    "reason": None,
                }
                _write_cache(ddb_client, cache_key, result, now_epoch + 1800)
                return result

        if results and all_zero:
            result = {
                "inr_hour": 0.0,
                "usd_hour": 0.0,
                "as_of_epoch": now_epoch,
                "staleness_seconds": 0,
                "granularity": "DAILY",
                "available": False,
                "reason": "no_data_yet",
            }
            _write_cache(ddb_client, cache_key, result, now_epoch + 1800)
            return result
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        reason = "not_enabled" if "DataUnavailable" in code else "error"
        result = {
            "inr_hour": 0.0,
            "usd_hour": 0.0,
            "as_of_epoch": now_epoch,
            "staleness_seconds": 0,
            "granularity": "DAILY",
            "available": False,
            "reason": reason,
        }
        _write_cache(ddb_client, cache_key, result, now_epoch + 1800)
        return result
    except Exception as exc:
        logger.warning(f"Daily cost query error: {exc}")
        return {
            "inr_hour": 0.0,
            "usd_hour": 0.0,
            "as_of_epoch": now_epoch,
            "staleness_seconds": 0,
            "granularity": "DAILY",
            "available": False,
            "reason": "error",
        }

    # If all queries completed without positive amounts
    return {
        "inr_hour": 0.0,
        "usd_hour": 0.0,
        "as_of_epoch": now_epoch,
        "staleness_seconds": 0,
        "granularity": "HOURLY",
        "available": False,
        "reason": "no_data_yet",
    }


def _write_cache(ddb_client: Optional[Any], cache_key: str, data: Dict[str, Any], ttl: int) -> None:
    """Store reported cost result in DynamoDB cache table."""
    if not ddb_client:
        return
    try:
        item: Dict[str, Any] = {
            "pk": {"S": cache_key},
            "ttl": {"N": str(ttl)},
            "inr_hour": {"N": str(data["inr_hour"])},
            "usd_hour": {"N": str(data["usd_hour"])},
            "as_of_epoch": {"N": str(data["as_of_epoch"])},
            "granularity": {"S": data["granularity"]},
            "available": {"BOOL": data["available"]},
        }
        if data.get("reason"):
            item["reason"] = {"S": str(data["reason"])}
        ddb_client.put_item(
            TableName=TABLE_PRICE_CACHE,
            Item=item,
        )
    except Exception as err:
        logger.warning(f"Failed to cache reported burn: {err}")
