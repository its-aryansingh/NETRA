"""
NETRA Human Approval Token Engine.
Implements single-use, time-bound (5-minute) HMAC-SHA256 cryptographic approval tokens.
Guarantees that the AI model cannot execute mutating remediations without an authentic,
human-authorized token minted via the Netra Cockpit UI.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional, Set, Tuple

SECRET_KEY = os.getenv("NETRA_APPROVAL_SECRET", "netra-secret-key-wemakedevs-2026").encode("utf-8")

# In-memory redeemed tokens set for fast single-use nonce tracking
_REDEEMED_TOKENS: Set[str] = set()


def hash_plan(plan: Any) -> str:
    """Compute canonical SHA-256 hash of a remediation plan."""
    if isinstance(plan, str):
        content = plan
    else:
        content = json.dumps(plan, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def mint_approval_token(
    finding_id: str,
    plan: Any,
    expires_in_seconds: int = 300,  # 5 minutes
    secret: Optional[bytes] = None,
) -> str:
    """
    Mints a signed approval token for human-authorized remediation.
    Payload: finding_id + plan_hash + expires_at + nonce
    """
    sec = secret or SECRET_KEY
    now = int(time.time())
    expires_at = now + expires_in_seconds
    ph = hash_plan(plan)
    nonce = os.urandom(8).hex()

    payload = {
        "fid": finding_id,
        "ph": ph,
        "exp": expires_at,
        "nonce": nonce,
    }

    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8")

    signature = hmac.new(sec, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_approval_token(
    token_str: str,
    finding_id: str,
    plan: Any,
    secret: Optional[bytes] = None,
    redeemed_tokens: Optional[Set[str]] = None,
) -> Tuple[bool, str]:
    """
    Verifies an approval token against signature, expiry, plan integrity, and replay defense.
    Returns (is_valid, reason).
    """
    if not token_str or "." not in token_str:
        return False, "Malformed approval token: missing signature delimiter"

    sec = secret or SECRET_KEY
    parts = token_str.split(".")
    if len(parts) != 2:
        return False, "Invalid token structure"

    payload_b64, signature = parts[0], parts[1]

    # 1. Verify HMAC Signature
    expected_sig = hmac.new(sec, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        return False, "Invalid cryptographic signature: token was tampered with or forged"

    # 2. Decode payload
    try:
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception as exc:
        return False, f"Failed to decode token payload: {exc}"

    # 3. Verify Expiry
    now = int(time.time())
    if payload.get("exp", 0) < now:
        return False, f"Approval token expired ({now - payload.get('exp', 0)}s ago). Maximum validity is 5 minutes"

    # 4. Verify Finding ID
    if payload.get("fid") != finding_id:
        return False, f"Token finding_id '{payload.get('fid')}' does not match target finding '{finding_id}'"

    # 5. Verify Plan Hash
    expected_ph = hash_plan(plan)
    if payload.get("ph") != expected_ph:
        return False, "Plan hash mismatch: remediation plan has deviated from human-approved specification"

    # 6. Verify Replay / Single-Use Nonce
    tracker = redeemed_tokens if redeemed_tokens is not None else _REDEEMED_TOKENS
    token_id = f"{payload.get('fid')}#{payload.get('nonce')}"
    if token_id in tracker:
        return False, "Approval token has already been redeemed (replay attack rejected)"

    # Mark redeemed
    tracker.add(token_id)
    return True, "Approval token verified and authorized"
