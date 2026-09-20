#!/usr/bin/env python3
"""NETRA Automated Chaos & Synthetic Load Testing Suite.

Executes 5 stress and resilience test scenarios:
1. High-concurrency runaway burst ingestion (<10s fast-path latency under load).
2. Cedar security policy enforcement under adverse conditions (100% denial of forbidden actions).
3. Cryptographic HMAC token tampering and replay prevention across MCP boundary.
4. Dead-endpoint resilience & zero unhandled exceptions on network timeout.
5. Mathematical paisa-precision conservation across multi-region resources.
"""

from __future__ import annotations

import concurrent.futures
import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure backend package is in sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Ensure stdout handles UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from netra.collector import run_fast_path
from netra.models import PricedResource
from netra.policy import check
from netra.mcp.tokens import mint_approval_token, verify_approval_token
from netra.notifications import dispatch_webhook, dispatch_slack_alert
from netra.inventory import total_inr_hour


def simulate_burst_ingestion(count: int = 10) -> Dict[str, Any]:
    """Stage 1: Simulates concurrent EC2 state-change notifications."""
    t0 = time.perf_counter()
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _trigger(i: int):
        event = {
            "id": f"evt-chaos-burst-{i}",
            "source": "aws.ec2",
            "detail-type": "EC2 Instance State-change Notification",
            "time": now_iso,
            "detail": {
                "instance-id": f"i-runaway-chaos-{i:03d}",
                "state": "running",
            },
        }
        return run_fast_path(event)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
        futures = [pool.submit(_trigger, i) for i in range(count)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    duration = time.perf_counter() - t0
    success = len(results) == count and all(r.get("status") == "ok" for r in results)
    max_latency_ms = max(r.get("detection_latency_ms", 0) for r in results)
    return {
        "success": success and max_latency_ms < 10000,
        "count": len(results),
        "duration_s": round(duration, 2),
        "max_latency_ms": max_latency_ms,
    }


def simulate_cedar_safeguards() -> Dict[str, Any]:
    """Stage 2: Verify Cedar forbid policies strictly block forbidden actions."""
    # Test 1: Protected resource
    res_protected = {
        "resource_id": "i-chaos-protected",
        "kind": "ec2",
        "tags": {"netra:protected": "true", "Owner": "finops"},
    }
    dec_protected = check("terminate", res_protected, {"has_snapshot_step": True})
    blocked_protected = not dec_protected.allowed and dec_protected.rule_id == "forbid_protected"

    # Test 2: Unsnapshotted destructive action
    res_ebs = {
        "resource_id": "vol-chaos-test",
        "kind": "ebs",
        "tags": {"Owner": "developer"},
    }
    dec_unsnap = check("delete", res_ebs, {"has_snapshot_step": False})
    blocked_unsnap = not dec_unsnap.allowed and dec_unsnap.rule_id == "forbid_unsnapshotted"

    # Test 3: Active dependent resource
    res_dep = {
        "resource_id": "i-chaos-with-dependents",
        "kind": "ec2",
        "tags": {"Owner": "lead"},
    }
    dec_dep = check("terminate", res_dep, {"dependent_count": 2, "has_snapshot_step": True})
    blocked_dep = not dec_dep.allowed and dec_dep.rule_id == "forbid_dependents"

    all_blocked = blocked_protected and blocked_unsnap and blocked_dep
    return {
        "success": all_blocked,
        "blocked_protected": blocked_protected,
        "blocked_unsnapshotted": blocked_unsnap,
        "blocked_dependents": blocked_dep,
    }


def simulate_token_tampering() -> Dict[str, Any]:
    """Stage 3: Verify HMAC signature tampering and replay attack refusal."""
    finding_id = "01CHAOSFINDING00000000000001"
    plan = {"action": "stop", "steps": ["ec2:StopInstances"]}
    token = mint_approval_token(finding_id, plan)

    redeemed: set[str] = set()
    # 1. Genuine redemption
    ok1, reason1 = verify_approval_token(token, finding_id, plan, redeemed_tokens=redeemed)

    # 2. Replay redemption (must fail)
    ok2, reason2 = verify_approval_token(token, finding_id, plan, redeemed_tokens=redeemed)
    replay_blocked = (not ok2) and ("replay" in reason2.lower())

    # 3. Tampered payload
    tampered_plan = {"action": "terminate", "steps": ["ec2:TerminateInstances"]}
    fresh_token = mint_approval_token(finding_id, plan)
    ok3, reason3 = verify_approval_token(fresh_token, finding_id, tampered_plan, redeemed_tokens=redeemed)
    tamper_blocked = not ok3

    success = ok1 and replay_blocked and tamper_blocked
    return {
        "success": success,
        "genuine_verified": ok1,
        "replay_blocked": replay_blocked,
        "tamper_blocked": tamper_blocked,
    }


def simulate_network_resilience() -> Dict[str, Any]:
    """Stage 4: Verify dead-endpoint webhook failure does not crash pipeline."""
    dead_url = "http://192.0.2.1:1/blackhole"
    ok = dispatch_webhook(dead_url, {"chaos": "test"}, timeout=1)
    # Must gracefully return False and NOT raise an unhandled exception
    return {
        "success": ok is False,
        "handled_gracefully": True,
    }


def simulate_precision_conservation() -> Dict[str, Any]:
    """Stage 5: Verify mathematical exactness across 50 multi-region resources."""
    resources = []
    expected_sum = 0.0
    regions = ["ap-south-1", "us-east-1", "eu-west-1"]

    for i in range(50):
        inr = round(10.25 + (i * 1.33), 2)
        expected_sum += inr
        res = PricedResource(
            resource_id=f"res-chaos-{i:03d}",
            kind="ec2" if i % 2 == 0 else "ebs",
            sub_type="c5.xlarge",
            region=regions[i % len(regions)],
            launched_at=1789740000,
            age_seconds=1800,
            usd_hour=round(inr / 88.50, 4),
            inr_hour=inr,
            price_ref="test:chaos",
            tags={"Owner": "finops"},
            state="running",
        )
        resources.append(res)

    computed_total = total_inr_hour(resources)
    expected_rounded = round(expected_sum, 2)
    diff = abs(computed_total - expected_rounded)
    success = diff < 0.001

    return {
        "success": success,
        "resources_count": len(resources),
        "computed_total_inr": computed_total,
        "expected_total_inr": expected_rounded,
        "drift": round(diff, 4),
    }


def run_chaos_suite() -> bool:
    """Execute all chaos test scenarios and report summary."""
    print("NETRA Chaos & Synthetic Load Testing Suite")
    print("=" * 60)

    stages = [
        ("Burst Ingestion Latency (<10s)", simulate_burst_ingestion),
        ("Cedar Policy Invariants (3/3)", simulate_cedar_safeguards),
        ("HMAC Tampering & Replay Defense", simulate_token_tampering),
        ("Dead-Endpoint Webhook Resilience", simulate_network_resilience),
        ("Paisa Mathematical Precision", simulate_precision_conservation),
    ]

    all_passed = True
    for name, fn in stages:
        t_start = time.perf_counter()
        try:
            res = fn()
            elapsed = time.perf_counter() - t_start
            ok = res.get("success", False)
            sym = "✓" if ok else "✗"
            print(f"  {sym} {name} [{elapsed:.2f}s]")
            if not ok:
                all_passed = False
                print(f"    Details: {res}")
        except Exception as exc:
            all_passed = False
            print(f"  ✗ {name} EXCEPTION: {exc}")

    print("=" * 60)
    status_str = "ALL CHAOS STAGES PASSED" if all_passed else "CHAOS SUITE FAILED"
    print(f"Result: {status_str}")
    return all_passed


if __name__ == "__main__":
    success = run_chaos_suite()
    sys.exit(0 if success else 1)
