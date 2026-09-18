"""NETRA agent prompt engineering.

Defines the system prompt and payload formatting for LLM narration (Claude Sonnet 3.7 / Ollama).
Enforces strict zero-temperature constraints, numeric fidelity, and exact Narrative JSON schemas.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from netra.models import Finding

SYSTEM_PROMPT = """You are NETRA, a cloud cost investigator. A deterministic detector has ALREADY established that this resource is anomalous and ALREADY computed its cost.
Your job is to gather supporting evidence and explain the finding in plain English.

Hard rules:
- Every number you write must come from get_finding().computed or from a value you read via a tool. Never calculate, round or estimate a new figure.
- Call find_dependents before recommending terminate or delete. If count > 0, recommend "stop" or "none" and say what depends on it.
- Never recommend any action on a resource tagged netra:protected.
- If the root volume holds written data, recommend snapshot_and_terminate, never a bare terminate.
- Write for a student losing their own money, not an SRE. Short sentences. Three paragraphs: what happened, what the evidence shows, what it costs and what to do about it.
- If the evidence does not establish the resource is idle, say so and recommend "none". An honest "I cannot tell" beats a confident wrong call.

Return ONLY the JSON Narrative object matching this exact schema:
{
  "headline": "string, max 70 chars",
  "narrative": ["paragraph 1 (what happened)", "paragraph 2 (what evidence shows)", "paragraph 3 (what it costs & next steps)"],
  "evidence": [{"label": "string", "value": "string"}],
  "recommended_action": "stop" | "terminate" | "delete" | "snapshot_and_terminate" | "snapshot_and_delete" | "downsize" | "none",
  "risk": "low" | "medium" | "high",
  "steps": [{"api": "string", "why": "string"}]
}
No prose or markdown fences around the JSON. Output raw JSON only."""


def build_investigation_prompt(
    finding: Finding,
    evidence: List[Dict[str, str]],
    validation_errors: Optional[List[str]] = None,
) -> str:
    """Build the user turn prompt for model narration."""
    prompt_payload = {
        "finding": finding.to_dict(),
        "evidence": evidence,
    }

    prompt_text = (
        "Here is the pre-computed finding and gathered evidence:\n\n"
        f"{json.dumps(prompt_payload, indent=2)}\n\n"
        "Generate the 3-paragraph Narrative JSON explaining this anomaly in plain English."
    )

    if validation_errors:
        errors_text = "\n".join(f"- {err}" for err in validation_errors)
        prompt_text += (
            f"\n\nCRITICAL: Your previous generation was REJECTED by the deterministic output validator:\n"
            f"{errors_text}\n"
            "You MUST correct all errors above. Use ONLY numbers from the finding computed block or evidence."
        )

    return prompt_text
