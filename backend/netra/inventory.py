"""NETRA inventory collection module.

Inventories running EC2 instances, unattached EBS volumes, and available NAT gateways.
Prices each resource using the deterministic pricing engine and returns a list of
PricedResource instances carrying cryptographic provenance.
"""

from __future__ import annotations

import concurrent.futures
import datetime
import time
from typing import Any, Dict, List, Optional

import boto3

from netra.config import REGION, get_logger
from netra.models import PricedResource
from netra.pricing import get_price

logger = get_logger("netra.inventory")


def _flatten_tags(tag_list: Optional[List[Dict[str, str]]]) -> Dict[str, Optional[str]]:
    """Flatten AWS Tag list [{'Key': k, 'Value': v}] to a dictionary.
    
    Guarantees 'Owner' and 'netra:protected' keys exist (defaulting to None).
    """
    result: Dict[str, Optional[str]] = {
        "Owner": None,
        "netra:protected": None,
    }
    if not tag_list:
        return result

    for tag in tag_list:
        key = tag.get("Key")
        if key:
            result[key] = tag.get("Value")
    return result


def _epoch_seconds(dt: Any) -> int:
    """Safely convert datetime or epoch value to integer seconds."""
    if isinstance(dt, (int, float)):
        return int(dt)
    if isinstance(dt, datetime.datetime):
        return int(dt.timestamp())
    return int(time.time())


def collect_single_region(
    session: Optional[boto3.Session] = None,
    region: str = REGION,
    dynamodb_client: Any = None,
    pricing_client: Any = None,
    s3_client: Any = None,
    bucket_name: Optional[str] = None,
) -> List[PricedResource]:
    """Discover active compute, unattached storage, and NAT gateways in target region.
    
    Prices each resource, carrying price_ref through. Any single resource pricing
    failure is logged and handled gracefully so the collection run never crashes.
    """
    sess = session or boto3.Session(region_name=region)
    ec2 = sess.client("ec2", region_name=region)
    now = int(time.time())
    priced_resources: List[PricedResource] = []

    # 1. EC2 Running Instances
    try:
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        ):
            for reservation in page.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    instance_id = inst["InstanceId"]
                    instance_type = inst["InstanceType"]
                    launched_at = _epoch_seconds(inst.get("LaunchTime", now))
                    age_seconds = max(0, now - launched_at)
                    tags = _flatten_tags(inst.get("Tags"))
                    meta = {
                        "vpc_id": inst.get("VpcId"),
                        "subnet_id": inst.get("SubnetId"),
                        "private_ip": inst.get("PrivateIpAddress"),
                        "public_ip": inst.get("PublicIpAddress"),
                    }

                    try:
                        price_doc = get_price(
                            kind="ec2",
                            sub_type=instance_type,
                            region=region,
                            dynamodb_client=dynamodb_client,
                            pricing_client=pricing_client,
                            s3_client=s3_client,
                            bucket_name=bucket_name,
                        )
                        priced_resources.append(
                            PricedResource(
                                resource_id=instance_id,
                                kind="ec2",
                                sub_type=instance_type,
                                region=region,
                                launched_at=launched_at,
                                age_seconds=age_seconds,
                                usd_hour=price_doc.usd_hour,
                                inr_hour=price_doc.inr_hour,
                                price_ref=price_doc.price_ref,
                                tags=tags,
                                state="running",
                                meta=meta,
                            )
                        )
                    except Exception as err:
                        logger.warning(
                            f"Failed to price EC2 instance {instance_id}: {err}",
                            extra={"resource_id": instance_id, "error": str(err)},
                        )
    except Exception as err:
        logger.warning(
            f"Failed to describe EC2 instances in {region}: {err}",
            extra={"region": region, "error": str(err)},
        )

    # 2. Unattached EBS Volumes (status=available)
    try:
        vol_paginator = ec2.get_paginator("describe_volumes")
        for page in vol_paginator.paginate(
            Filters=[{"Name": "status", "Values": ["available"]}]
        ):
            for vol in page.get("Volumes", []):
                volume_id = vol["VolumeId"]
                volume_type = vol.get("VolumeType", "gp3")
                size_gb = int(vol.get("Size", 8))
                created_at = _epoch_seconds(vol.get("CreateTime", now))
                age_seconds = max(0, now - created_at)
                tags = _flatten_tags(vol.get("Tags"))
                meta = {
                    "size_gb": size_gb,
                    "iops": vol.get("Iops"),
                    "throughput": vol.get("Throughput"),
                    "availability_zone": vol.get("AvailabilityZone"),
                }

                try:
                    price_doc = get_price(
                        kind="ebs",
                        sub_type=volume_type,
                        region=region,
                        size_gb=size_gb,
                        dynamodb_client=dynamodb_client,
                        pricing_client=pricing_client,
                        s3_client=s3_client,
                        bucket_name=bucket_name,
                    )
                    priced_resources.append(
                        PricedResource(
                            resource_id=volume_id,
                            kind="ebs",
                            sub_type=volume_type,
                            region=region,
                            launched_at=created_at,
                            age_seconds=age_seconds,
                            usd_hour=price_doc.usd_hour,
                            inr_hour=price_doc.inr_hour,
                            price_ref=price_doc.price_ref,
                            tags=tags,
                            state="available",
                            meta=meta,
                        )
                    )
                except Exception as err:
                    logger.warning(
                        f"Failed to price EBS volume {volume_id}: {err}",
                        extra={"resource_id": volume_id, "error": str(err)},
                    )
    except Exception as err:
        logger.warning(
            f"Failed to describe EBS volumes in {region}: {err}",
            extra={"region": region, "error": str(err)},
        )

    # 3. Available NAT Gateways
    try:
        nat_paginator = ec2.get_paginator("describe_nat_gateways")
        for page in nat_paginator.paginate(
            Filters=[{"Name": "state", "Values": ["available"]}]
        ):
            for nat in page.get("NatGateways", []):
                nat_id = nat["NatGatewayId"]
                created_at = _epoch_seconds(nat.get("CreateTime", now))
                age_seconds = max(0, now - created_at)
                tags = _flatten_tags(nat.get("Tags"))
                meta = {
                    "vpc_id": nat.get("VpcId"),
                    "subnet_id": nat.get("SubnetId"),
                }

                try:
                    price_doc = get_price(
                        kind="nat",
                        sub_type="nat",
                        region=region,
                        dynamodb_client=dynamodb_client,
                        pricing_client=pricing_client,
                        s3_client=s3_client,
                        bucket_name=bucket_name,
                    )
                    priced_resources.append(
                        PricedResource(
                            resource_id=nat_id,
                            kind="nat",
                            sub_type="nat",
                            region=region,
                            launched_at=created_at,
                            age_seconds=age_seconds,
                            usd_hour=price_doc.usd_hour,
                            inr_hour=price_doc.inr_hour,
                            price_ref=price_doc.price_ref,
                            tags=tags,
                            state="available",
                            meta=meta,
                        )
                    )
                except Exception as err:
                    logger.warning(
                        f"Failed to price NAT Gateway {nat_id}: {err}",
                        extra={"resource_id": nat_id, "error": str(err)},
                    )
    except Exception as err:
        logger.warning(
            f"Failed to describe NAT Gateways in {region}: {err}",
            extra={"region": region, "error": str(err)},
        )

    return priced_resources


def collect(
    session: Optional[boto3.Session] = None,
    region: str = REGION,
    dynamodb_client: Any = None,
    pricing_client: Any = None,
    regions: Optional[List[str]] = None,
    s3_client: Any = None,
    bucket_name: Optional[str] = None,
) -> List[PricedResource]:
    """Discover active compute, unattached storage, and NAT gateways across target region(s).
    
    If `regions` contains multiple regions, runs collection across all specified
    regions concurrently and aggregates the resulting priced inventory.
    """
    if regions and len(regions) > 1:
        results: List[PricedResource] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(regions), 8)) as executor:
            futures = {
                executor.submit(collect_single_region, session, reg, dynamodb_client, pricing_client, s3_client, bucket_name): reg
                for reg in regions
            }
            for fut in concurrent.futures.as_completed(futures):
                reg_name = futures[fut]
                try:
                    res_list = fut.result()
                    results.extend(res_list)
                except Exception as exc:
                    logger.warning(f"Error collecting inventory from region {reg_name}: {exc}")
        return sorted(results, key=lambda x: x.resource_id)

    target_region = regions[0] if (regions and len(regions) == 1) else region
    return collect_single_region(session, target_region, dynamodb_client, pricing_client, s3_client, bucket_name)


def total_inr_hour(resources: List[PricedResource]) -> float:
    """Calculate cumulative spend rate in INR per hour across all inventoried resources."""
    return round(sum(r.inr_hour for r in resources), 2)


def total_usd_hour(resources: List[PricedResource]) -> float:
    """Calculate cumulative spend rate in USD per hour across all inventoried resources."""
    return round(sum(r.usd_hour for r in resources), 4)


def by_service(resources: List[PricedResource]) -> Dict[str, float]:
    """Aggregate total INR per hour partitioned by service kind ('ec2', 'ebs', 'nat')."""
    breakdown: Dict[str, float] = {
        "ec2": 0.0,
        "ebs": 0.0,
        "nat": 0.0,
    }
    for r in resources:
        breakdown[r.kind] = round(breakdown.get(r.kind, 0.0) + r.inr_hour, 2)
    return breakdown


def by_region(resources: List[PricedResource]) -> Dict[str, float]:
    """Aggregate total INR per hour partitioned by AWS region."""
    breakdown: Dict[str, float] = {}
    for r in resources:
        breakdown[r.region] = round(breakdown.get(r.region, 0.0) + r.inr_hour, 2)
    return breakdown
