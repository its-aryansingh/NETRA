"""NETRA SNS notification publisher for critical findings.

Delivers concise, actionable alerts to phone/email via AWS SNS within
strict character limits:
- Subject: < 100 characters (e.g. NETRA: Rs 66.55/hr — c5.4xlarge i-0a4f39c7b12e8d5a1)
- Message Body: < 300 characters (headline, burn projections, cockpit deep link)
"""

from __future__ import annotations

import os
from typing import Any, Optional
import boto3

from netra.config import REGION, get_logger

logger = get_logger("netra.notify")


def publish_critical(
    finding: Any,
    narrative: Optional[Any] = None,
    session: Optional[boto3.Session] = None,
    region: Optional[str] = None,
) -> bool:
    """Publish a critical finding notification to the NETRA SNS alert topic.

    Guarantees:
    - Never raises an exception; returns False on any error or missing topic ARN.
    - Subject is strictly < 100 characters.
    - Message body is strictly < 300 characters.
    - Returns True if successfully published to SNS.
    """
    try:
        from netra.config import SNS_TOPIC_ARN
        topic_arn = (
            os.environ.get("NETRA_ALERT_TOPIC_ARN")
            or SNS_TOPIC_ARN
            or os.environ.get("SNS_TOPIC_ARN")
            or os.environ.get("NETRA_SNS_TOPIC_ARN")
            or ""
        ).strip()

        if not topic_arn:
            logger.debug("NETRA_ALERT_TOPIC_ARN not configured; skipping SNS publish")
            return False

        # Extract finding attributes whether Finding dataclass or dict
        if isinstance(finding, dict):
            fid = finding.get("finding_id", "unknown")
            res = finding.get("resource", {})
            comp = finding.get("computed", {})
            f_narrative = finding.get("narrative")
        else:
            fid = getattr(finding, "finding_id", "unknown")
            res = getattr(finding, "resource", None)
            comp = getattr(finding, "computed", {}) or {}
            f_narrative = getattr(finding, "narrative", None)

        effective_narrative = narrative or f_narrative

        # Extract resource fields
        if isinstance(res, dict):
            res_id = str(res.get("resource_id", "unknown"))
            sub_type = str(res.get("sub_type", "resource"))
            res_inr_hour = res.get("inr_hour", 0.0)
        elif res is not None:
            res_id = str(getattr(res, "resource_id", "unknown"))
            sub_type = str(getattr(res, "sub_type", "resource"))
            res_inr_hour = getattr(res, "inr_hour", 0.0)
        else:
            res_id = "unknown"
            sub_type = "resource"
            res_inr_hour = 0.0

        # Extract computed financial metrics
        inr_hour = float(comp.get("inr_hour", res_inr_hour) or 0.0)
        inr_month = float(comp.get("inr_month", round(inr_hour * 730, 2)) or 0.0)
        runway_hours = float(comp.get("runway_hours", 0.0) or 0.0)

        # Extract headline
        if isinstance(effective_narrative, dict):
            headline = effective_narrative.get("headline", "")
        elif effective_narrative is not None:
            headline = getattr(effective_narrative, "headline", "")
        else:
            headline = ""

        if not headline:
            headline = f"Critical runaway {sub_type} spend detected"

        # Shorten resource_id if necessary
        res_id_short = res_id if len(res_id) <= 22 else f"{res_id[:19]}..."

        # Subject: NETRA: Rs {inr_hour}/hr — {sub_type} {resource_id_short} (< 100 chars)
        inr_hour_str = f"{inr_hour:.2f}" if inr_hour != int(inr_hour) else f"{int(inr_hour)}"
        subject = f"NETRA: Rs {inr_hour_str}/hr — {sub_type} {res_id_short}"
        if len(subject) > 99:
            subject = subject[:96] + "..."

        # Format body:
        # {headline}
        #
        # Rs {inr_month}/month if it keeps running.
        # Credits gone in {runway_hours}h.
        #
        # Approve or dismiss: {NETRA_DASHBOARD_URL}/investigations/{finding_id}
        dashboard_url = os.environ.get("NETRA_DASHBOARD_URL", "https://netra.bharatbuilds.dev").rstrip("/")
        link_line = f"Approve or dismiss: {dashboard_url}/investigations/{fid}"
        inr_month_str = f"{inr_month:,.2f}" if inr_month != int(inr_month) else f"{int(inr_month):,}"
        runway_str = f"{runway_hours:.1f}" if runway_hours != int(runway_hours) else f"{int(runway_hours)}"

        body_suffix = (
            f"\n\nRs {inr_month_str}/month if it keeps running.\n"
            f"Credits gone in {runway_str}h.\n\n"
            f"{link_line}"
        )

        max_headline_len = 299 - len(body_suffix)
        if max_headline_len < 10:
            headline = headline[:30] + "..."
            body = f"{headline}{body_suffix}"[:299]
        else:
            if len(headline) > max_headline_len:
                headline = headline[: max_headline_len - 3] + "..."
            body = f"{headline}{body_suffix}"

        # Ensure strict constraint < 300
        if len(body) >= 300:
            body = body[:296] + "..."

        target_region = region or os.environ.get("AWS_DEFAULT_REGION") or REGION
        sess = session or boto3.Session(region_name=target_region)
        sns_client = sess.client("sns", region_name=target_region)

        sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=body,
        )
        logger.info(f"Published critical finding alert to SNS topic {topic_arn} for {fid}")
        return True

    except Exception as exc:
        logger.warning(f"Failed to publish critical finding alert to SNS: {exc}")
        return False
