"""
NETRA Append-Only Audit Ledger.
Provides immutable tracking of all remediation authorizations, executions,
revert actions, and recovered spend against DynamoDB netra_audit_log.
"""

import time
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
import boto3

from netra.config import AUDIT_TABLE, DEFAULT_ACCOUNT_ID
from netra.models import _to_decimal, _from_decimal

logger = logging.getLogger("netra.audit")


def record_audit_entry(
    session: Optional[boto3.Session],
    account_id: str,
    finding_id: str,
    action: str,
    target_id: str,
    approved_by: str,
    recovered_month_inr: float,
    rollback_snapshot_id: Optional[str] = None,
    ok: bool = True,
    error: Optional[str] = None,
    table_name: str = AUDIT_TABLE,
) -> Dict[str, Any]:
    """
    Appends an immutable audit record to netra_audit_log.
    SK format: AUD#<epoch_ms>#<finding_id>
    """
    epoch_ms = int(time.time() * 1000)
    audit_id = f"AUD#{epoch_ms}#{finding_id}"
    now_ts = int(time.time())

    item = {
        "pk": f"ACCOUNT#{account_id}",
        "sk": audit_id,
        "audit_id": audit_id,
        "finding_id": finding_id,
        "action": action,
        "target_id": target_id,
        "approved_by": approved_by,
        "recovered_month_inr": _to_decimal(round(recovered_month_inr, 2)),
        "rollback_snapshot_id": rollback_snapshot_id or "none",
        "ok": ok,
        "error": error or "",
        "timestamp": now_ts,
        "ttl": now_ts + (90 * 86400),  # 90 days retention
    }

    sess = session or boto3.Session()
    dynamodb = sess.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        table.put_item(Item=item)
        logger.info(
            "Recorded audit entry %s for action %s on %s (ok=%s)",
            audit_id,
            action,
            target_id,
            ok,
        )
    except Exception as exc:
        logger.error("Failed to write audit record %s: %s", audit_id, exc)
        raise

    return _from_decimal(item)


def get_audit_entries(
    session: Optional[boto3.Session],
    account_id: str = DEFAULT_ACCOUNT_ID,
    limit: int = 50,
    table_name: str = AUDIT_TABLE,
) -> Dict[str, Any]:
    """
    Queries audit log descending by timestamp.
    Returns list of audit items with recovered month total and counts.
    """
    sess = session or boto3.Session()
    dynamodb = sess.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        res = table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": f"ACCOUNT#{account_id}"},
            ScanIndexForward=False,
            Limit=limit,
        )
        raw_items = res.get("Items", [])
    except Exception as exc:
        logger.warning("Audit query failed (%s), returning empty list", exc)
        raw_items = []

    clean_items = [_from_decimal(it) for it in raw_items]
    recovered_total = sum(
        it.get("recovered_month_inr", 0.0) for it in clean_items if it.get("ok", True)
    )
    action_count = sum(1 for it in clean_items if it.get("ok", True))
    revert_count = sum(1 for it in clean_items if it.get("action") == "revert")

    return {
        "entries": clean_items,
        "recovered_month_inr": round(recovered_total, 2),
        "action_count": action_count,
        "revert_count": revert_count,
    }
