"""NETRA agent investigation tools.

Provides 5 read-only tools for gathering supporting evidence during an investigation:
1. get_finding(finding_id)
2. get_resource_details(resource_id)
3. get_cloudwatch_utilization(resource_id, minutes)
4. find_dependents(resource_id)
5. get_burn_timeline(hours)

All tools return JSON-serializable dictionaries and record execution latencies
for the UI agent_trace display.
"""

from __future__ import annotations

import datetime
import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from netra.config import REGION, TABLE_BURN_SNAPSHOTS, TABLE_FINDINGS, get_logger
from netra.models import Finding, PricedResource

logger = get_logger("netra.agent.tools")


class ToolTracker:
    """Records execution durations for invoked tools to populate agent_trace."""

    def __init__(self) -> None:
        self.traces: List[Dict[str, Any]] = []

    def record(
        self,
        tool_name: str,
        duration_ms: int,
        success: bool = True,
        via: Optional[str] = None,
    ) -> None:
        boundary = via if via is not None else ("mcp" if tool_name.startswith(("netra_", "mcp_")) else "direct")
        self.traces.append({
            "tool": tool_name,
            "ms": duration_ms,
            "success": success,
            "via": boundary,
        })

    def get_traces(self) -> List[Dict[str, Any]]:
        return list(self.traces)


def get_finding(
    finding_id: str,
    dynamodb_client: Any = None,
    table_name: str = TABLE_FINDINGS,
    account_id: str = "default",
    tracker: Optional[ToolTracker] = None,
) -> Dict[str, Any]:
    """Retrieve computed Finding document by finding_id."""
    start = time.time()
    result: Dict[str, Any] = {}
    try:
        if dynamodb_client:
            res = dynamodb_client.get_item(
                TableName=table_name,
                Key={
                    "pk": {"S": f"ACCOUNT#{account_id}"},
                    "sk": {"S": f"FIND#{finding_id}"},
                },
            )
            item = res.get("Item")
            if item:
                # Unpack finding item
                parsed: Dict[str, Any] = {}
                for k, v in item.items():
                    if "S" in v:
                        parsed[k] = v["S"]
                    elif "N" in v:
                        parsed[k] = float(v["N"]) if "." in v["N"] else int(v["N"])
                    elif "M" in v:
                        parsed[k] = v["M"]
                result = parsed
    except Exception as err:
        logger.warning(f"Tool get_finding failed for {finding_id}: {err}")
    finally:
        elapsed = int((time.time() - start) * 1000)
        if tracker:
            tracker.record("get_finding", max(1, elapsed), bool(result))

    return result


def get_resource_details(
    resource_id: str,
    session: Optional[boto3.Session] = None,
    region: str = REGION,
    tracker: Optional[ToolTracker] = None,
) -> Dict[str, Any]:
    """Inspect EC2, EBS, or NAT resource details, tags, and attachments."""
    start = time.time()
    sess = session or boto3.Session(region_name=region)
    ec2 = sess.client("ec2", region_name=region)
    details: Dict[str, Any] = {
        "resource_id": resource_id,
        "region": region,
        "state": "unknown",
        "tags": {},
        "attached_volumes": [],
    }

    try:
        if resource_id.startswith("i-"):
            res = ec2.describe_instances(InstanceIds=[resource_id])
            for r in res.get("Reservations", []):
                for inst in r.get("Instances", []):
                    details["state"] = inst.get("State", {}).get("Name", "running")
                    details["instance_type"] = inst.get("InstanceType")
                    details["launched_at"] = str(inst.get("LaunchTime"))
                    details["vpc_id"] = inst.get("VpcId")
                    details["subnet_id"] = inst.get("SubnetId")
                    details["tags"] = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                    details["attached_volumes"] = [
                        {
                            "volume_id": b.get("Ebs", {}).get("VolumeId"),
                            "device": b.get("DeviceName"),
                            "delete_on_termination": b.get("Ebs", {}).get("DeleteOnTermination", True),
                        }
                        for b in inst.get("BlockDeviceMappings", [])
                    ]
        elif resource_id.startswith("vol-"):
            res = ec2.describe_volumes(VolumeIds=[resource_id])
            for v in res.get("Volumes", []):
                details["state"] = v.get("State", "available")
                details["size_gb"] = v.get("Size")
                details["volume_type"] = v.get("VolumeType")
                details["tags"] = {t["Key"]: t["Value"] for t in v.get("Tags", [])}
                details["attachments"] = v.get("Attachments", [])
        elif resource_id.startswith("nat-"):
            res = ec2.describe_nat_gateways(NatGatewayIds=[resource_id])
            for n in res.get("NatGateways", []):
                details["state"] = n.get("State", "available")
                details["vpc_id"] = n.get("VpcId")
                details["subnet_id"] = n.get("SubnetId")
                details["tags"] = {t["Key"]: t["Value"] for t in n.get("Tags", [])}
    except Exception as err:
        logger.warning(f"Tool get_resource_details failed for {resource_id}: {err}")
    finally:
        elapsed = int((time.time() - start) * 1000)
        if tracker:
            tracker.record("get_resource_details", max(1, elapsed))

    return details


def get_cloudwatch_utilization(
    resource_id: str,
    minutes: int = 60,
    session: Optional[boto3.Session] = None,
    region: str = REGION,
    tracker: Optional[ToolTracker] = None,
) -> Dict[str, Any]:
    """Retrieve detailed utilization metrics for a resource over the last N minutes."""
    start = time.time()
    sess = session or boto3.Session(region_name=region)
    cw = sess.client("cloudwatch", region_name=region)
    now = datetime.datetime.now(datetime.timezone.utc)
    start_time = now - datetime.timedelta(minutes=minutes)

    util: Dict[str, Any] = {
        "resource_id": resource_id,
        "window_minutes": minutes,
        "cpu_utilization_max": 0.0,
        "cpu_utilization_avg": 0.0,
        "network_packets_out": 0,
        "network_bytes_out": 0,
        "ebs_read_ops": 0,
        "ebs_write_ops": 0,
    }

    try:
        queries = [
            {
                "Id": "m_cpu_max",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EC2",
                        "MetricName": "CPUUtilization",
                        "Dimensions": [{"Name": "InstanceId", "Value": resource_id}],
                    },
                    "Period": 300,
                    "Stat": "Maximum",
                },
                "ReturnData": True,
            },
            {
                "Id": "m_cpu_avg",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EC2",
                        "MetricName": "CPUUtilization",
                        "Dimensions": [{"Name": "InstanceId", "Value": resource_id}],
                    },
                    "Period": 300,
                    "Stat": "Average",
                },
                "ReturnData": True,
            },
            {
                "Id": "m_net_packets",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EC2",
                        "MetricName": "NetworkPacketsOut",
                        "Dimensions": [{"Name": "InstanceId", "Value": resource_id}],
                    },
                    "Period": 300,
                    "Stat": "Sum",
                },
                "ReturnData": True,
            },
            {
                "Id": "m_net_out",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EC2",
                        "MetricName": "NetworkOut",
                        "Dimensions": [{"Name": "InstanceId", "Value": resource_id}],
                    },
                    "Period": 300,
                    "Stat": "Sum",
                },
                "ReturnData": True,
            },
        ]

        resp = cw.get_metric_data(
            MetricDataQueries=queries,
            StartTime=start_time,
            EndTime=now,
        )

        for res in resp.get("MetricDataResults", []):
            vals = res.get("Values", [])
            qid = res.get("Id")
            if qid == "m_cpu_max" and vals:
                util["cpu_utilization_max"] = round(max(vals), 2)
            elif qid == "m_cpu_avg" and vals:
                util["cpu_utilization_avg"] = round(sum(vals) / len(vals), 2)
            elif qid == "m_net_packets" and vals:
                util["network_packets_out"] = int(sum(vals))
            elif qid == "m_net_out" and vals:
                util["network_bytes_out"] = int(sum(vals))
    except Exception as err:
        logger.warning(f"Tool get_cloudwatch_utilization failed for {resource_id}: {err}")
    finally:
        elapsed = int((time.time() - start) * 1000)
        if tracker:
            tracker.record("get_cloudwatch_utilization", max(1, elapsed))

    return util


def find_dependents(
    resource_id: str,
    session: Optional[boto3.Session] = None,
    region: str = REGION,
    tracker: Optional[ToolTracker] = None,
) -> Dict[str, Any]:
    """Inspect dependent architecture components (ELBs, ASGs, route tables, security groups)."""
    start = time.time()
    sess = session or boto3.Session(region_name=region)
    items: List[Dict[str, str]] = []

    try:
        # Check ELB target groups if instance
        if resource_id.startswith("i-"):
            try:
                elbv2 = sess.client("elbv2", region_name=region)
                tg_resp = elbv2.describe_target_groups()
                for tg in tg_resp.get("TargetGroups", []):
                    tg_arn = tg["TargetGroupArn"]
                    th = elbv2.describe_target_health(TargetGroupArn=tg_arn)
                    for desc in th.get("TargetHealthDescriptions", []):
                        if desc.get("Target", {}).get("Id") == resource_id:
                            items.append({
                                "type": "TargetGroup",
                                "name": tg.get("TargetGroupName", "tg"),
                                "arn": tg_arn,
                            })
            except Exception:
                pass

            # Check Auto Scaling Groups
            try:
                asg = sess.client("autoscaling", region_name=region)
                asg_resp = asg.describe_auto_scaling_instances(InstanceIds=[resource_id])
                for inst in asg_resp.get("AutoScalingInstances", []):
                    items.append({
                        "type": "AutoScalingGroup",
                        "name": inst.get("AutoScalingGroupName", "asg"),
                    })
            except Exception:
                pass

        # Check Route tables if NAT gateway
        elif resource_id.startswith("nat-"):
            try:
                ec2 = sess.client("ec2", region_name=region)
                rts = ec2.describe_route_tables(
                    Filters=[{"Name": "route.nat-gateway-id", "Values": [resource_id]}]
                )
                for rt in rts.get("RouteTables", []):
                    items.append({
                        "type": "RouteTable",
                        "id": rt["RouteTableId"],
                    })
            except Exception:
                pass

    except Exception as err:
        logger.warning(f"Tool find_dependents failed for {resource_id}: {err}")
    finally:
        elapsed = int((time.time() - start) * 1000)
        if tracker:
            tracker.record("find_dependents", max(1, elapsed))

    return {
        "resource_id": resource_id,
        "count": len(items),
        "items": items,
    }


def get_burn_timeline(
    hours: int = 6,
    dynamodb_client: Any = None,
    account_id: str = "default",
    table_name: str = TABLE_BURN_SNAPSHOTS,
    tracker: Optional[ToolTracker] = None,
) -> Dict[str, Any]:
    """Retrieve historical burn rate timeline and identify step change timestamps."""
    start = time.time()
    now_epoch = int(time.time())
    start_epoch = now_epoch - (hours * 3600)
    timeline: Dict[str, Any] = {
        "points": [],
        "baseline": 0.0,
        "step_at_ts": None,
        "by_service": {"ec2": 0.0, "ebs": 0.0, "nat": 0.0},
    }

    try:
        if dynamodb_client:
            resp = dynamodb_client.query(
                TableName=table_name,
                KeyConditionExpression="pk = :pk AND sk >= :start_sk",
                ExpressionAttributeValues={
                    ":pk": {"S": f"ACCOUNT#{account_id}"},
                    ":start_sk": {"S": f"TS#{start_epoch}"},
                },
                Limit=360,
            )
            pts = []
            for it in resp.get("Items", []):
                ts = int(it["sk"]["S"].replace("TS#", ""))
                inr = float(it["total_inr_hour"]["N"])
                pts.append({"ts": ts, "inr_hour": inr})
            timeline["points"] = pts
            if pts:
                timeline["baseline"] = round(pts[0]["inr_hour"], 2)
    except Exception as err:
        logger.warning(f"Tool get_burn_timeline failed: {err}")
    finally:
        elapsed = int((time.time() - start) * 1000)
        if tracker:
            tracker.record("get_burn_timeline", max(1, elapsed))

    return timeline
