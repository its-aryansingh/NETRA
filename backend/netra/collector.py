"""NETRA collector module.

Executes on a 1-minute schedule:
1. Discovers and prices all running EC2 instances, unattached EBS volumes, and NAT gateways.
2. Writes a burn rate snapshot to `netra_burn_snapshots` (7-day TTL).
3. Reads the last 60 snapshot totals to establish a rolling median baseline.
4. Queries CloudWatch for candidate resource utilization in a SINGLE batched get_metric_data call.
5. Queries existing open findings from `netra_findings` to prevent duplicate alerts.
6. Evaluates deterministic rules using `detector.evaluate()`.
7. Persists new Findings (`status="DETECTED"`).
8. Emits a `netra.finding.created` EventBridge event for each new Finding.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
import json
import os
import time
from typing import Any, Dict, List, Optional, Set

import boto3
from botocore.exceptions import ClientError

from netra.config import (
    REGION,
    TABLE_BURN_SNAPSHOTS,
    TABLE_FINDINGS,
    get_logger,
)
from netra.detector import evaluate
from netra.inventory import by_service, collect, total_inr_hour, total_usd_hour
from netra.models import Finding, PricedResource

logger = get_logger("netra.collector")


def _get_cloudwatch_metrics_batch(
    cloudwatch_client: Any,
    resources: List[PricedResource],
    now_epoch: int,
) -> Dict[str, Dict[str, Any]]:
    """Batch fetch utilization metrics from CloudWatch in a single get_metric_data request."""
    if not cloudwatch_client or not resources:
        return {}

    metric_queries: List[Dict[str, Any]] = []
    # Map query ID back to (resource_id, metric_field)
    query_id_map: Dict[str, tuple[str, str]] = {}

    idx = 0
    for res in resources:
        if res.kind == "ec2":
            q_cpu = f"m_cpu_{idx}"
            metric_queries.append({
                "Id": q_cpu,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EC2",
                        "MetricName": "CPUUtilization",
                        "Dimensions": [{"Name": "InstanceId", "Value": res.resource_id}],
                    },
                    "Period": 300,
                    "Stat": "Maximum",
                },
                "ReturnData": True,
            })
            query_id_map[q_cpu] = (res.resource_id, "cpu_max_pct")

            q_net = f"m_net_{idx}"
            metric_queries.append({
                "Id": q_net,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EC2",
                        "MetricName": "NetworkPacketsOut",
                        "Dimensions": [{"Name": "InstanceId", "Value": res.resource_id}],
                    },
                    "Period": 300,
                    "Stat": "Sum",
                },
                "ReturnData": True,
            })
            query_id_map[q_net] = (res.resource_id, "network_packets_out")
            idx += 1

        elif res.kind == "nat":
            q_bytes = f"m_bytes_{idx}"
            metric_queries.append({
                "Id": q_bytes,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/NATGateway",
                        "MetricName": "BytesOutToDestination",
                        "Dimensions": [{"Name": "NatGatewayId", "Value": res.resource_id}],
                    },
                    "Period": 300,
                    "Stat": "Sum",
                },
                "ReturnData": True,
            })
            query_id_map[q_bytes] = (res.resource_id, "bytes_out")
            idx += 1

    if not metric_queries:
        return {}

    # Query last 60 minutes of data
    start_time = datetime.datetime.fromtimestamp(now_epoch - 3600, tz=datetime.timezone.utc)
    end_time = datetime.datetime.fromtimestamp(now_epoch, tz=datetime.timezone.utc)

    results_by_resource: Dict[str, Dict[str, Any]] = {}

    try:
        response = cloudwatch_client.get_metric_data(
            MetricDataQueries=metric_queries,
            StartTime=start_time,
            EndTime=end_time,
        )

        for result in response.get("MetricDataResults", []):
            qid = result.get("Id")
            values = result.get("Values", [])
            if qid in query_id_map and values:
                resource_id, field_name = query_id_map[qid]
                if resource_id not in results_by_resource:
                    results_by_resource[resource_id] = {}
                if field_name == "cpu_max_pct":
                    results_by_resource[resource_id][field_name] = round(max(values), 2)
                elif field_name == "network_packets_out":
                    results_by_resource[resource_id][field_name] = int(sum(values))
                elif field_name == "bytes_out":
                    results_by_resource[resource_id][field_name] = int(sum(values))
    except Exception as err:
        logger.warning(f"Batch CloudWatch metric query failed: {err}")

    return results_by_resource


def _get_recent_baseline_totals(
    dynamodb_client: Any,
    account_id: str = "default",
    table_name: str = TABLE_BURN_SNAPSHOTS,
) -> List[float]:
    """Retrieve the last up to 60 snapshot burn rates from netra_burn_snapshots."""
    if not dynamodb_client:
        return []

    try:
        response = dynamodb_client.query(
            TableName=table_name,
            KeyConditionExpression="pk = :pk AND begins_with(sk, :sk_prefix)",
            ExpressionAttributeValues={
                ":pk": {"S": f"ACCOUNT#{account_id}"},
                ":sk_prefix": {"S": "TS#"},
            },
            ScanIndexForward=False,  # Newest first
            Limit=60,
        )
        items = response.get("Items", [])
        totals: List[float] = []
        for it in items:
            total_val = it.get("total_inr_hour")
            if total_val and "N" in total_val:
                totals.append(float(total_val["N"]))
            elif total_val and isinstance(total_val, (int, float)):
                totals.append(float(total_val))
        return list(reversed(totals))  # Chronological order
    except Exception as err:
        logger.warning(f"Failed to query historical burn snapshots: {err}")
        return []


def _get_open_finding_resource_ids(
    dynamodb_client: Any,
    table_name: str = TABLE_FINDINGS,
) -> Set[str]:
    """Query open findings from netra_findings GSI status-index to prevent duplicates."""
    if not dynamodb_client:
        return set()

    active_statuses = ["DETECTED", "NARRATING", "AWAITING_APPROVAL"]
    open_resource_ids: Set[str] = set()

    for st in active_statuses:
        try:
            response = dynamodb_client.query(
                TableName=table_name,
                IndexName="status-index",
                KeyConditionExpression="#st = :status_val",
                ExpressionAttributeNames={"#st": "status"},
                ExpressionAttributeValues={":status_val": {"S": st}},
            )
            for item in response.get("Items", []):
                # Extract resource_id from nested resource or top-level
                res_id = None
                if "resource_id" in item:
                    res_id = item["resource_id"].get("S")
                elif "resource" in item:
                    res_map = item["resource"].get("M", {})
                    if "resource_id" in res_map:
                        res_id = res_map["resource_id"].get("S")
                if res_id:
                    open_resource_ids.add(res_id)
        except Exception as err:
            logger.warning(f"Failed to query status-index for {st}: {err}")

    return open_resource_ids


def _save_snapshot(
    dynamodb_client: Any,
    resources: List[PricedResource],
    now_epoch: int,
    account_id: str = "default",
    table_name: str = TABLE_BURN_SNAPSHOTS,
) -> None:
    """Save the current inventory burn snapshot with a 7-day TTL."""
    if not dynamodb_client:
        return

    tot_inr = total_inr_hour(resources)
    tot_usd = total_usd_hour(resources)
    svc_breakdown = by_service(resources)
    ttl_epoch = now_epoch + (7 * 86400)

    try:
        item = {
            "pk": {"S": f"ACCOUNT#{account_id}"},
            "sk": {"S": f"TS#{now_epoch}"},
            "total_inr_hour": {"N": str(tot_inr)},
            "total_usd_hour": {"N": str(tot_usd)},
            "by_service": {"M": {k: {"N": str(v)} for k, v in svc_breakdown.items()}},
            "resource_count": {"N": str(len(resources))},
            "ttl": {"N": str(ttl_epoch)},
            "created_at": {"N": str(now_epoch)},
        }
        dynamodb_client.put_item(TableName=table_name, Item=item)
        logger.info(f"Recorded snapshot: ₹{tot_inr}/hr across {len(resources)} resources")
    except Exception as err:
        logger.warning(f"Failed writing burn snapshot: {err}")


def _save_finding(
    dynamodb_client: Any,
    finding: Finding,
    table_name: str = TABLE_FINDINGS,
) -> None:
    """Persist new finding to netra_findings table."""
    if not dynamodb_client:
        return

    try:
        dynamo_item = finding.to_item()
        # Convert to low-level attribute map if client is boto3 client
        wire_item: Dict[str, Any] = {}
        for k, v in dynamo_item.items():
            if isinstance(v, str):
                wire_item[k] = {"S": v}
            elif isinstance(v, (int, float, Decimal)):
                wire_item[k] = {"N": str(v)}
            elif isinstance(v, dict):
                wire_item[k] = {"S": json.dumps(v, default=str)}
            elif isinstance(v, list):
                wire_item[k] = {"S": json.dumps(v, default=str)}
            else:
                wire_item[k] = {"S": str(v)}

        # Specifically ensure GSI attributes are clean
        wire_item["status"] = {"S": finding.status}
        wire_item["detected_at"] = {"N": str(finding.detected_at)}
        wire_item["resource_id"] = {"S": finding.resource.resource_id}

        dynamodb_client.put_item(TableName=table_name, Item=wire_item)
        logger.info(f"Persisted finding {finding.finding_id} for {finding.resource.resource_id}")
    except Exception as err:
        logger.warning(f"Failed writing finding to DynamoDB: {err}")


def _emit_finding_event(
    events_client: Any,
    finding: Finding,
    event_bus: str = "default",
) -> None:
    """Emit netra.finding.created event to EventBridge."""
    if not events_client:
        return

    try:
        events_client.put_events(
            Entries=[
                {
                    "Source": "netra.collector",
                    "DetailType": "netra.finding.created",
                    "Detail": json.dumps(finding.to_dict(), default=str),
                    "EventBusName": event_bus,
                }
            ]
        )
        logger.info(f"Emitted netra.finding.created event for {finding.finding_id}")
    except Exception as err:
        logger.warning(f"Failed to emit EventBridge event for {finding.finding_id}: {err}")


def run_collector(
    session: Optional[boto3.Session] = None,
    region: str = REGION,
    account_id: str = "default",
    event_bus: str = "default",
) -> Dict[str, Any]:
    """Execute complete collection, snapshotting, metric gathering, and detection cycle."""
    sess = session or boto3.Session(region_name=region)
    now_epoch = int(time.time())

    # Initialize AWS clients safely
    try:
        dynamo = sess.client("dynamodb", region_name=region)
    except Exception:
        dynamo = None

    try:
        cw = sess.client("cloudwatch", region_name=region)
    except Exception:
        cw = None

    try:
        events = sess.client("events", region_name=region)
    except Exception:
        events = None

    logger.info("Starting NETRA inventory collection...")
    # 1. Collect inventory & prices
    resources = collect(session=sess, region=region, dynamodb_client=dynamo)
    tot_inr = total_inr_hour(resources)
    tot_usd = total_usd_hour(resources)

    # 2. Persist snapshot
    _save_snapshot(dynamo, resources, now_epoch, account_id=account_id)

    # 3. Read historical baseline totals
    baseline_history = _get_recent_baseline_totals(dynamo, account_id=account_id)

    # 4. Fetch CloudWatch metrics in a single batch
    metrics = _get_cloudwatch_metrics_batch(cw, resources, now_epoch)

    # 5. Query open findings to deduplicate
    open_ids = _get_open_finding_resource_ids(dynamo)

    # 6. Evaluate pure detector
    snapshot_data = {
        "total_inr_hour": tot_inr,
        "resources": resources,
    }
    new_findings = evaluate(
        snapshot=snapshot_data,
        baseline_history=baseline_history,
        metrics=metrics,
        detected_at=now_epoch,
        open_finding_resource_ids=open_ids,
        account_id=account_id,
    )

    # 7. Persist findings & emit EventBridge events
    for f in new_findings:
        _save_finding(dynamo, f)
        _emit_finding_event(events, f, event_bus=event_bus)

    summary = {
        "status": "ok",
        "collected_at": now_epoch,
        "total_inr_hour": tot_inr,
        "total_usd_hour": tot_usd,
        "resources_count": len(resources),
        "new_findings_count": len(new_findings),
        "findings": [f.finding_id for f in new_findings],
    }
    logger.info(f"Collector completed: {summary}")
    return summary


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry point for scheduled collector execution."""
    return run_collector()


if __name__ == "__main__":
    # Local CLI runner
    res = run_collector()
    logger.info(
        f"NETRA Burn Rate: INR {res['total_inr_hour']}/hr (${res['total_usd_hour']}/hr) "
        f"across {res['resources_count']} resources. New findings: {res['new_findings_count']}"
    )
