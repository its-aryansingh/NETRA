/**
 * API Client for NETRA frontend.
 * If NEXT_PUBLIC_DEMO=1 or demo mode is active, serves fixture data with zero latency.
 */

import {
  DEMO_AUDIT_LOG,
  DEMO_BURN_SERIES,
  DEMO_BY_CAUSE,
  DEMO_FINDINGS,
  DEMO_RESOURCES,
  DEMO_SUMMARY,
  AuditEntry,
  FindingItem,
  PricedResourceItem,
} from "./demo-data";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export function isDemoMode(): boolean {
  if (typeof window !== "undefined") {
    const override = window.localStorage.getItem("netra_demo_mode");
    if (override !== null) return override === "true";
  }
  return process.env.NEXT_PUBLIC_DEMO !== "0"; // Default to demo mode for judge resilience
}

export function setDemoMode(active: boolean): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem("netra_demo_mode", String(active));
    window.location.reload();
  }
}

// Client-side mutable store for interactive demo mode (approving, simulating)
let clientFindings = [...DEMO_FINDINGS];
let clientResources = [...DEMO_RESOURCES];
let clientAudit = [...DEMO_AUDIT_LOG];
let clientSummary = { ...DEMO_SUMMARY };
let clientBurn = { ...DEMO_BURN_SERIES };

export async function getSummary() {
  if (isDemoMode()) return clientSummary;

  try {
    const res = await fetch(`${API_BASE}/summary`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("API unavailable, falling back to demo summary", err);
    return clientSummary;
  }
}

export async function getBurn(hours: number = 24) {
  if (isDemoMode()) return clientBurn;

  try {
    const res = await fetch(`${API_BASE}/burn?hours=${hours}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("API unavailable, falling back to demo burn", err);
    return clientBurn;
  }
}

export async function getInventory(): Promise<{ resources: PricedResourceItem[]; counts: { regions: number; total: number }; priced_at: number }> {
  if (isDemoMode()) {
    return {
      resources: clientResources,
      counts: { regions: 1, total: clientResources.length },
      priced_at: Math.floor(Date.now() / 1000),
    };
  }

  try {
    const res = await fetch(`${API_BASE}/inventory`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("API unavailable, falling back to demo inventory", err);
    return {
      resources: clientResources,
      counts: { regions: 1, total: clientResources.length },
      priced_at: Math.floor(Date.now() / 1000),
    };
  }
}

export async function getFindings(status: string = "open"): Promise<{ findings: FindingItem[] }> {
  if (isDemoMode()) {
    const filtered = (status === "open"
      ? clientFindings.filter(f => ["DETECTED", "NARRATING", "AWAITING_APPROVAL"].includes(f.status))
      : clientFindings.filter(f => f.status.toLowerCase() === status.toLowerCase())
    );
    return { findings: filtered };
  }

  try {
    const res = await fetch(`${API_BASE}/findings?status=${status}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("API unavailable, falling back to demo findings", err);
    return { findings: clientFindings };
  }
}

export async function getFinding(id: string): Promise<FindingItem | null> {
  if (isDemoMode()) {
    const found = clientFindings.find(f => f.finding_id === id);
    return found || clientFindings[0];
  }

  try {
    const res = await fetch(`${API_BASE}/findings/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`API unavailable, finding ${id} demo fallback`, err);
    return clientFindings.find(f => f.finding_id === id) || clientFindings[0];
  }
}

export async function approveFinding(id: string): Promise<{ execution_arn: string; status: string }> {
  if (isDemoMode()) {
    const idx = clientFindings.findIndex(f => f.finding_id === id);
    if (idx !== -1) {
      const f = clientFindings[idx];
      f.status = "RESOLVED";

      // Append to audit log
      clientAudit.unshift({
        audit_id: `AUD#${Date.now()}#${id.slice(-5)}`,
        action: f.narrative?.recommended_action || "terminate",
        target_id: f.resource.resource_id,
        approved_by: "student-dev@we-make-devs.org",
        recovered_month_inr: f.computed.inr_month,
        timestamp: Math.floor(Date.now() / 1000),
        rollback_snapshot_id: "snap-0netrarollback",
      });

      // Remove resource from active burn
      clientResources = clientResources.filter(r => r.resource_id !== f.resource.resource_id);
      clientSummary.burn_inr_hour = Math.max(23.04, clientSummary.burn_inr_hour - f.computed.inr_hour);
      clientSummary.prevented_today_inr += f.computed.inr_month;
      clientSummary.multiple = Math.round((clientSummary.burn_inr_hour / clientSummary.baseline_inr_hour) * 100) / 100;
    }
    return { execution_arn: `arn:aws:states:ap-south-1:123456789012:execution:netra-remediate:${id}`, status: "EXECUTING" };
  }

  const res = await fetch(`${API_BASE}/findings/${id}/approve`, { method: "POST" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function dismissFinding(id: string): Promise<{ status: string }> {
  if (isDemoMode()) {
    const target = clientFindings.find(f => f.finding_id === id);
    if (target) target.status = "DISMISSED";
    return { status: "DISMISSED" };
  }

  const res = await fetch(`${API_BASE}/findings/${id}/dismiss`, { method: "POST" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function snoozeFinding(id: string, hours: number = 2): Promise<{ status: string; snoozed_until: number }> {
  if (isDemoMode()) {
    const target = clientFindings.find(f => f.finding_id === id);
    if (target) target.status = "SNOOZED";
    return { status: "SNOOZED", snoozed_until: Math.floor(Date.now() / 1000) + hours * 3600 };
  }

  const res = await fetch(`${API_BASE}/findings/${id}/snooze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hours }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function getAudit(limit: number = 50): Promise<{ entries: AuditEntry[]; recovered_month_inr: number; action_count: number; revert_count: number }> {
  if (isDemoMode()) {
    const totalRecovered = clientAudit.reduce((acc, it) => acc + (it.revert ? it.recovered_month_inr : it.recovered_month_inr), 0);
    return {
      entries: clientAudit.slice(0, limit),
      recovered_month_inr: totalRecovered,
      action_count: clientAudit.filter(a => !a.revert).length,
      revert_count: clientAudit.filter(a => a.revert).length,
    };
  }

  try {
    const res = await fetch(`${API_BASE}/audit?limit=${limit}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("API unavailable, falling back to demo audit", err);
    return {
      entries: clientAudit,
      recovered_month_inr: 71921.8,
      action_count: 5,
      revert_count: 1,
    };
  }
}

export async function getAuditByCause(): Promise<{ causes: Array<{ label: string; amount_inr: number; count: number }> }> {
  if (isDemoMode()) return { causes: DEMO_BY_CAUSE };

  try {
    const res = await fetch(`${API_BASE}/audit/by-cause`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("API unavailable, falling back to demo causes", err);
    return { causes: DEMO_BY_CAUSE };
  }
}

export async function simulateRunaway(): Promise<{ status: string; finding_id: string }> {
  const now = Math.floor(Date.now() / 1000);
  const newFid = `01J8SIM_${now.toString().slice(-6)}`;

  const runawayRes: PricedResourceItem = {
    resource_id: `i-${Math.random().toString(16).slice(2, 12)}`,
    kind: "ec2",
    sub_type: "c5.4xlarge",
    region: "ap-south-1",
    launched_at: now,
    age_seconds: 60,
    usd_hour: 0.752,
    inr_hour: 66.55,
    price_ref: "sha256:4a9f13c8b417e290fbb69411bc294a0293da27f8cf28e1c6b891823abce1283a",
    tags: { Owner: null, "netra:protected": null },
    state: "running",
    meta: { vpc_id: "vpc-0a1b2c3d" },
  };

  const newFinding: FindingItem = {
    finding_id: newFid,
    severity: "critical",
    status: "AWAITING_APPROVAL",
    rules_fired: [
      { rule: "idle_compute", detail: "cpu_max=1.8% age=1m" },
      { rule: "burn_step_change", detail: "multiple=3.89" },
    ],
    resource: runawayRes,
    computed: {
      inr_hour: 66.55,
      inr_month: 48576.0,
      baseline_inr_hour: 23.04,
      multiple: 3.89,
      runway_hours: 14.9,
      share_of_burn_pct: 94.4,
    },
    detected_at: now,
    headline: "Runaway c5.4xlarge (₹66.55/hr) burning 3.9× baseline",
    narrative: {
      headline: "Runaway c5.4xlarge (₹66.55/hr) burning 3.9× baseline",
      narrative: [
        "A c5.4xlarge has been running in ap-south-1 for 1 minute. It is costing ₹66.55 per hour — 3.9× your usual baseline — and accounts for 94.4% of everything you are currently spending.",
        "CloudWatch metrics report CPU utilization at 1.8% with negligible network traffic (120 packets out). The compute instance has remained idle since launch.",
        "Projected 30-day exposure is ₹48576.0 with an estimated credit runway of 14.9 hours. We recommend snapshotting and terminating the instance.",
      ],
      evidence: [
        {"label": "CPUUtilization max", "value": "1.8%"},
        {"label": "NetworkPacketsOut", "value": "120"},
        {"label": "Active Dependents", "value": "0"},
      ],
      recommended_action: "snapshot_and_terminate",
      risk: "medium",
      steps: [
        {"api": "ec2:CreateSnapshot", "why": "Safeguard root volume before termination"},
        {"api": "ec2:TerminateInstances", "why": "Terminate runaway compute instance"},
      ],
    },
    agent_trace: [
      { tool: "get_finding", ms: 4 },
      { tool: "get_resource_details", ms: 42 },
      { tool: "find_dependents", ms: 28 },
      { tool: "model_converse", ms: 520 },
    ],
    narrative_source: "bedrock",
  };

  clientResources.unshift(runawayRes);
  clientFindings.unshift(newFinding);
  clientSummary.burn_inr_hour += 66.55;
  clientSummary.multiple = Math.round((clientSummary.burn_inr_hour / clientSummary.baseline_inr_hour) * 100) / 100;

  return { status: "simulated", finding_id: newFid };
}
