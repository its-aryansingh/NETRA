"""
NETRA CloudWatch Custom Metrics Emitter.
Publishes real-time telemetry into the 'NETRA' namespace:
- BurnRateINRPerHour: Current spend velocity (₹/hr)
- DetectionLatencyMs: Fast-path EventBridge detection latency (ms)
- OpenFindings: Count of unresolved findings
- RecoveredINR: Spend preserved via remediation

Guaranteed safety: Never raises or interrupts caller execution.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import boto3

from netra.config import REGION, get_logger

logger = get_logger("netra.metrics")


def put_metric(
    name: str,
    value: float,
    unit: str = "None",
    dimensions: Optional[Dict[str, str]] = None,
    session: Optional[boto3.Session] = None,
    region: str = REGION,
) -> bool:
    """Publish custom metric to CloudWatch namespace 'NETRA'.
    
    Shielded against all network, permission, and throttling exceptions.
    Returns True if successfully sent, False otherwise.
    """
    try:
        sess = session or boto3.Session(region_name=region)
        cw = sess.client("cloudwatch", region_name=region)
        
        metric_item: Dict[str, Any] = {
            "MetricName": name,
            "Value": float(value),
            "Unit": unit,
        }
        if dimensions:
            metric_item["Dimensions"] = [
                {"Name": k, "Value": str(v)} for k, v in dimensions.items()
            ]

        cw.put_metric_data(
            Namespace="NETRA",
            MetricData=[metric_item],
        )
        logger.debug(f"Emitted metric {name}={value} ({unit}) to namespace NETRA")
        return True
    except Exception as exc:
        # Non-blocking failure: metrics failure must never break core workflow
        logger.debug(f"CloudWatch put_metric suppressed exception for {name}: {exc}")
        return False
