"""NETRA notification dispatcher.

Dispatches rich Slack Block Kit alert cards with interactive buttons and
generic webhook JSON payloads when critical spend anomalies are detected.
Zero external runtime dependencies (pure standard library urllib).
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from netra.config import get_logger
from netra.models import Finding

logger = get_logger("netra.notifications")


def build_slack_blocks(
    finding: Finding,
    inr_hour: float,
    runway_hours: float,
    cockpit_url: str = "https://netra.dev",
) -> Dict[str, Any]:
    """Construct a Slack Block Kit payload with actionable metadata and deep links."""
    res = finding.resource
    fid = finding.finding_id
    res_id = res.resource_id
    kind = res.kind
    sub_type = res.sub_type
    region = res.region
    inr_month = round(inr_hour * 730, 2)

    rules_fired = [r.get("rule", "") for r in finding.rules_fired]
    rules_text = ", ".join(rules_fired) if rules_fired else "spend_anomaly"
    headline = (finding.narrative.headline if finding.narrative else "Runaway Cloud Spend Detected")[:120]

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🚨 NETRA Alert: {finding.severity.upper()} Spend Detected",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{headline}*\nAutomated detection identified an unbudgeted spend velocity spike.",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Resource:*\n`{res_id}` ({sub_type})"},
                {"type": "mrkdwn", "text": f"*Region:*\n{region}"},
                {"type": "mrkdwn", "text": f"*Current Burn:*\n*₹{inr_hour:.2f}/hr*"},
                {"type": "mrkdwn", "text": f"*30-Day Projected:*\n₹{inr_month:,.2f}"},
                {"type": "mrkdwn", "text": f"*Credit Runway:*\n{runway_hours:.1f} hours remaining"},
                {"type": "mrkdwn", "text": f"*Rules Fired:*\n`{rules_text}`"},
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve Remediation ⚡", "emoji": True},
                    "style": "danger",
                    "url": f"{cockpit_url}/findings/{fid}",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Inspect in Cockpit 🔍", "emoji": True},
                    "url": f"{cockpit_url}/findings/{fid}",
                },
            ],
        },
    ]

    return {"text": f"🚨 NETRA Alert: ₹{inr_hour:.2f}/hr runaway on {res_id}", "blocks": blocks}


def dispatch_slack_alert(
    webhook_url: str,
    finding: Finding,
    inr_hour: Optional[float] = None,
    runway_hours: Optional[float] = None,
    cockpit_url: str = "https://netra.dev",
    timeout: int = 5,
) -> bool:
    """Dispatch Slack Block Kit message to incoming webhook."""
    if not webhook_url:
        logger.debug("No Slack webhook URL configured; skipping.")
        return False

    comp = finding.computed or {}
    burn_rate = inr_hour if inr_hour is not None else comp.get("inr_hour", finding.resource.inr_hour)
    runway = runway_hours if runway_hours is not None else comp.get("runway_hours", 14.9)

    payload = build_slack_blocks(finding, burn_rate, runway, cockpit_url)
    return dispatch_webhook(webhook_url, payload, timeout=timeout)


def dispatch_webhook(
    webhook_url: str,
    payload: Dict[str, Any],
    timeout: int = 5,
) -> bool:
    """Send JSON payload via HTTP POST to arbitrary webhook endpoint."""
    if not webhook_url:
        return False

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "NETRA-Agent/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if 200 <= status < 300:
                logger.info(f"Successfully dispatched webhook to {webhook_url[:30]}... (status={status})")
                return True
            logger.warning(f"Webhook returned non-2xx status: {status}")
            return False
    except urllib.error.HTTPError as err:
        logger.warning(f"Webhook HTTPError {err.code}: {err.reason}")
        return False
    except Exception as exc:
        logger.warning(f"Failed to dispatch webhook to {webhook_url[:30]}...: {exc}")
        return False


def dispatch_external_alerts(
    finding: Finding,
    cockpit_url: str = "https://netra.dev",
) -> Dict[str, bool]:
    """Check environment variables and fan out alerts to Slack and generic webhooks."""
    results: Dict[str, bool] = {"slack": False, "webhook": False}
    slack_url = os.getenv("NETRA_SLACK_WEBHOOK_URL", "")
    generic_url = os.getenv("NETRA_GENERIC_WEBHOOK_URL", "")

    if slack_url:
        results["slack"] = dispatch_slack_alert(slack_url, finding, cockpit_url=cockpit_url)

    if generic_url:
        finding_payload = {
            "event": "netra.finding.alert",
            "finding": finding.to_dict(),
            "timestamp": finding.detected_at,
        }
        results["webhook"] = dispatch_webhook(generic_url, finding_payload)

    return results
