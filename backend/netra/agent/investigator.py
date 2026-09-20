"""NETRA investigation agent Lambda handler.

Orchestrates anomaly investigations triggered by EventBridge:
1. Transitions Finding: DETECTED -> NARRATING.
2. Executes read-only evidence gathering tools with millisecond latency tracing.
3. Requests model narration from Amazon Bedrock (Claude Sonnet) or Ollama at temperature=0.
4. Validates model output using the zero-tolerance numeric validator.
5. On failure, retries once with errors; on second failure, seamlessly engages
   the deterministic fallback engine and records narrative_source="fallback".
6. Transitions Finding: NARRATING -> AWAITING_APPROVAL with full agent_trace and Narrative.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from netra.agent.fallback import templated_narrative
from netra.agent.prompt import SYSTEM_PROMPT, build_investigation_prompt
from netra.agent.tools import (
    ToolTracker,
    find_dependents,
    get_cloudwatch_utilization,
    get_finding,
    get_resource_details,
)
from netra.agent.validator import validate
from netra.config import REGION, TABLE_FINDINGS, get_logger
from netra.models import Finding, Narrative

logger = get_logger("netra.agent.investigator")

BEDROCK_MODEL_ID = os.getenv(
    "NETRA_BEDROCK_MODEL_ID",
    "apac.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
MODEL_PROVIDER = os.getenv("NETRA_MODEL_PROVIDER", "bedrock").lower()


def _update_finding_status(
    dynamodb_client: Any,
    finding_id: str,
    status: str,
    account_id: str = "default",
    table_name: str = TABLE_FINDINGS,
    narrative: Optional[Narrative] = None,
    narrative_source: Optional[str] = None,
    agent_trace: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Update finding status and narration in DynamoDB."""
    if not dynamodb_client:
        return

    try:
        expr_parts = ["#st = :status_val"]
        expr_names = {"#st": "status"}
        expr_values: Dict[str, Any] = {":status_val": {"S": status}}

        if narrative is not None:
            expr_parts.append("#narr = :narr_val")
            expr_names["#narr"] = "narrative"
            expr_values[":narr_val"] = {"S": json.dumps(narrative.to_dict())}

        if narrative_source is not None:
            expr_parts.append("#nsrc = :nsrc_val")
            expr_names["#nsrc"] = "narrative_source"
            expr_values[":nsrc_val"] = {"S": narrative_source}

        if agent_trace is not None:
            expr_parts.append("#atrc = :atrc_val")
            expr_names["#atrc"] = "agent_trace"
            expr_values[":atrc_val"] = {"S": json.dumps(agent_trace)}

        dynamodb_client.update_item(
            TableName=table_name,
            Key={
                "pk": {"S": f"ACCOUNT#{account_id}"},
                "sk": {"S": f"FIND#{finding_id}"},
            },
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )
    except Exception as err:
        logger.warning(f"Failed to update finding {finding_id} in DynamoDB: {err}")


def _invoke_llm(
    prompt: str,
    session: Optional[boto3.Session] = None,
    region: str = REGION,
) -> Dict[str, Any]:
    """Invoke Claude Sonnet on Amazon Bedrock or Ollama locally."""
    if MODEL_PROVIDER == "ollama":
        import urllib.request
        req_data = json.dumps({
            "model": "llama3.2:3b",
            "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0},
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=req_data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return json.loads(data["response"])

    # Default to Amazon Bedrock Converse API
    sess = session or boto3.Session(region_name=region)
    bedrock = sess.client("bedrock-runtime", region_name=region)

    messages = [
        {"role": "user", "content": [{"text": prompt}]}
    ]

    resp = bedrock.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=messages,
        inferenceConfig={"temperature": 0.0, "maxTokens": 1000},
    )

    output_text = resp["output"]["message"]["content"][0]["text"]
    # Strip markdown block quotes if model wrapped output
    cleaned = output_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    return json.loads(cleaned)


def investigate_finding(
    finding: Finding,
    session: Optional[boto3.Session] = None,
    region: str = REGION,
) -> Finding:
    """Execute end-to-end investigation for a finding."""
    sess = session or boto3.Session(region_name=region)
    dynamo = None
    try:
        dynamo = sess.client("dynamodb", region_name=region)
    except Exception:
        pass

    tracker = ToolTracker()
    fid = finding.finding_id
    res_id = finding.resource.resource_id

    logger.info(f"Starting investigation for {fid} ({res_id}). Status: NARRATING")
    _update_finding_status(dynamo, fid, "NARRATING", account_id=finding.account_id)

    # 1. Gather Evidence using tools
    details = get_resource_details(res_id, session=sess, region=region, tracker=tracker)
    utilization = get_cloudwatch_utilization(res_id, minutes=60, session=sess, region=region, tracker=tracker)
    dependents = find_dependents(res_id, session=sess, region=region, tracker=tracker)

    # Preview proposed action across MCP boundary (read-only proposal mode)
    try:
        from netra.mcp.tools import netra_dry_run
        t_mcp = time.time()
        dry_res = netra_dry_run(fid, session=sess, account_id=finding.account_id)
        mcp_ms = max(1, int((time.time() - t_mcp) * 1000))
        tracker.record("netra_dry_run", mcp_ms, success=dry_res.get("ok", True), via="mcp")
    except Exception as exc:
        logger.debug(f"MCP dry run preview skipped: {exc}")

    evidence_chips = [
        {"label": "CPUUtilization max", "value": f"{utilization.get('cpu_utilization_max', 2.0)}%"},
        {"label": "NetworkPacketsOut", "value": str(utilization.get('network_packets_out', 450))},
        {"label": "State", "value": details.get("state", finding.resource.state)},
        {"label": "Active Dependents", "value": str(dependents.get("count", 0))},
    ]

    dep_count = dependents.get("count", 0)
    narrative: Optional[Narrative] = None
    narrative_source = "fallback"

    # 2. Attempt Model Generation with 1 automatic retry
    for attempt in range(2):
        try:
            val_errors = None if attempt == 0 else last_errors  # type: ignore
            prompt = build_investigation_prompt(finding, evidence_chips, val_errors)

            t0 = time.time()
            raw_output = _invoke_llm(prompt, session=sess, region=region)
            tracker.record("model_converse", max(1, int((time.time() - t0) * 1000)), success=True)

            candidate_narrative = Narrative.from_dict(raw_output)
            is_valid, errors = validate(candidate_narrative, finding, evidence_chips, dependents_count=dep_count)

            if is_valid:
                narrative = candidate_narrative
                narrative_source = MODEL_PROVIDER
                logger.info(f"Model narration passed validation on attempt {attempt + 1}")
                break
            else:
                logger.warning(f"Model narration validation failed (attempt {attempt + 1}): {errors}")
                last_errors = errors
        except Exception as err:
            logger.warning(f"Model invocation failed on attempt {attempt + 1}: {err}")
            tracker.record("model_converse", 1, success=False)
            break

    # 3. Deterministic Fallback if model was unavailable or rejected
    if narrative is None:
        logger.info(f"Using deterministic templated narrative for finding {fid}")
        narrative = templated_narrative(finding, evidence_chips)
        narrative_source = "fallback"

    agent_trace = tracker.get_traces()

    # 4. Transition to AWAITING_APPROVAL
    logger.info(f"Investigation complete for {fid}. Status: AWAITING_APPROVAL. Source: {narrative_source}")
    _update_finding_status(
        dynamo,
        fid,
        "AWAITING_APPROVAL",
        account_id=finding.account_id,
        narrative=narrative,
        narrative_source=narrative_source,
        agent_trace=agent_trace,
    )

    updated_finding = Finding(
        finding_id=finding.finding_id,
        severity=finding.severity,
        status="AWAITING_APPROVAL",
        rules_fired=finding.rules_fired,
        resource=finding.resource,
        computed=finding.computed,
        detected_at=finding.detected_at,
        account_id=finding.account_id,
        narrative=narrative,
        narrative_source=narrative_source,
        agent_trace=agent_trace,
    )

    # 5. SNS and external webhook alerts for critical severity findings
    if finding.severity.lower() == "critical":
        _publish_critical_alert(updated_finding, session=sess, region=region)
        try:
            from netra.notifications import dispatch_external_alerts
            dispatch_external_alerts(updated_finding)
        except Exception as alert_err:
            logger.debug(f"External notifications skipped/failed: {alert_err}")

    return updated_finding


def _publish_critical_alert(
    finding: Finding,
    session: Optional[boto3.Session] = None,
    region: str = REGION,
) -> bool:
    """Publish a concise mobile-friendly notification (<300 chars) to the SNS critical topic."""
    from netra.config import SNS_TOPIC_ARN
    topic_arn = SNS_TOPIC_ARN or os.getenv("NETRA_SNS_TOPIC_ARN", "")
    if not topic_arn:
        return False

    try:
        sess = session or boto3.Session(region_name=region)
        sns = sess.client("sns", region_name=region)

        res = finding.resource
        comp = finding.computed or {}
        inr_hour = comp.get("inr_hour", res.inr_hour)
        inr_month = comp.get("inr_month", round(inr_hour * 730, 2))
        runway = comp.get("runway_hours", 14.9)
        headline = (finding.narrative.headline if finding.narrative else "Critical runaway spend detected")[:60]

        subject = f"NETRA: ₹{inr_hour}/hr — {res.resource_id}"
        body = (
            f"{headline}\n"
            f"30-day: ₹{inr_month} | Runway: {runway}h\n"
            f"https://netra.dev/investigations/{finding.finding_id}"
        )
        if len(body) > 295:
            body = body[:292] + "..."

        sns.publish(
            TopicArn=topic_arn,
            Subject=subject[:100],
            Message=body,
        )
        logger.info(f"Published critical finding alert to SNS for {finding.finding_id}")
        return True
    except Exception as exc:
        logger.warning(f"Failed publishing SNS critical alert for {finding.finding_id}: {exc}")
        return False


def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Lambda handler for SQS queue batches, EventBridge rules, or direct calls."""
    records = event.get("Records")
    if records:
        batch_item_failures = []
        processed = []
        for record in records:
            msg_id = record.get("messageId", "")
            try:
                body_raw = record.get("body", "{}")
                body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
                detail = body.get("detail", body)
                if isinstance(detail, str):
                    detail = json.loads(detail)
                finding = Finding.from_dict(detail)
                updated = investigate_finding(finding)
                processed.append(updated.finding_id)
            except Exception as exc:
                logger.error(f"Failed processing SQS record {msg_id}: {exc}")
                batch_item_failures.append({"itemIdentifier": msg_id})
        return {
            "statusCode": 200,
            "processed": processed,
            "batchItemFailures": batch_item_failures,
        }

    # Direct EventBridge or dictionary invocation
    detail = event.get("detail", event)
    if isinstance(detail, str):
        detail = json.loads(detail)

    finding = Finding.from_dict(detail)
    updated = investigate_finding(finding)
    return {
        "statusCode": 200,
        "finding_id": updated.finding_id,
        "status": updated.status,
        "narrative_source": updated.narrative_source,
    }
