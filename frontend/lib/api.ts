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

const _RAW_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").trim();

export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const custom = window.localStorage.getItem("netra_live_api_url");
    if (custom && custom.trim()) {
      const clean = custom.trim().replace(/\/+$/, "");
      return clean.endsWith("/api") ? clean : `${clean}/api`;
    }
  }

  if (_RAW_BASE) {
    const clean = _RAW_BASE.replace(/\/+$/, "");
    return clean.endsWith("/api") ? clean : `${clean}/api`;
  }

  if (process.env.NEXT_PUBLIC_DEMO !== "1" && !_RAW_BASE) {
    if (typeof window !== "undefined" && !isDemoMode()) {
      throw new Error(
        "NEXT_PUBLIC_API_BASE is not set. " +
        "When running in live mode (NEXT_PUBLIC_DEMO !== '1'), you must configure NEXT_PUBLIC_API_BASE " +
        "pointing to your deployed API Gateway endpoint (e.g. https://<api-id>.execute-api.ap-south-1.amazonaws.com)."
      );
    }
  }

  return "/api";
}

// Dynamically evaluates getApiBase() on every template string interpolation
const API_BASE = {
  toString: () => getApiBase(),
  valueOf: () => getApiBase(),
};

export function isDemoMode(): boolean {
  if (typeof window !== "undefined") {
    const override = window.localStorage.getItem("netra_demo_mode");
    if (override !== null) return override === "true";
    // If a custom live AWS API URL is configured, default to live mode
    if (window.localStorage.getItem("netra_live_api_url")) return false;
  }
  return process.env.NEXT_PUBLIC_DEMO === "1";
}

export function setDemoMode(active: boolean): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem("netra_demo_mode", String(active));
    window.location.reload();
  }
}

export function getConnectedAwsAccount(): { accountId: string; region: string; endpoint: string } | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem("netra_aws_account");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setConnectedAwsAccount(info: { accountId: string; region: string; endpoint: string } | null): void {
  if (typeof window === "undefined") return;
  if (!info) {
    window.localStorage.removeItem("netra_aws_account");
    window.localStorage.removeItem("netra_live_api_url");
    window.localStorage.removeItem("netra_demo_mode");
  } else {
    window.localStorage.setItem("netra_aws_account", JSON.stringify(info));
    if (info.endpoint) {
      window.localStorage.setItem("netra_live_api_url", info.endpoint);
    }
    window.localStorage.setItem("netra_demo_mode", "false");
  }
}

export async function testAwsConnection(endpoint: string): Promise<{ ok: boolean; message: string; latency_ms?: number; burn_inr_hour?: number }> {
  const t0 = performance.now();
  try {
    const clean = endpoint.trim().replace(/\/+$/, "");
    const url = clean.endsWith("/api") ? `${clean}/summary` : `${clean}/api/summary`;
    const res = await fetch(url, { headers: { "Content-Type": "application/json" } });
    const latency = Math.round(performance.now() - t0);
    if (!res.ok) {
      return { ok: false, message: `HTTP ${res.status}: Received error response from endpoint.` };
    }
    const data = await res.json();
    return {
      ok: true,
      message: `Connected successfully (${latency}ms). Active burn: ₹${data.burn_inr_hour || 0}/hr`,
      latency_ms: latency,
      burn_inr_hour: data.burn_inr_hour,
    };
  } catch (err: any) {
    return { ok: false, message: err.message || "Network error. Check CORS configuration or URL." };
  }
}

// ----------------------------------------------------------------------------
// Enterprise Auth & RBAC State (eauth)
// ----------------------------------------------------------------------------

export interface UserProfile {
  user_id: string;
  role: "admin" | "operator" | "viewer";
  name: string;
  token?: string;
  permissions?: string[];
  auth_type?: string;
}

const DEFAULT_USER: UserProfile = {
  user_id: "demo-operator@we-make-devs.org",
  role: "operator",
  name: "FinOps SRE Operator",
  permissions: ["view", "approve", "mutate"],
  auth_type: "demo_default",
};

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("netra_auth_token");
}

export function getCurrentUser(): UserProfile {
  if (typeof window === "undefined") return DEFAULT_USER;
  const raw = window.localStorage.getItem("netra_user_profile");
  if (!raw) return DEFAULT_USER;
  try {
    return JSON.parse(raw);
  } catch {
    return DEFAULT_USER;
  }
}

export function getAuthHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getAuthToken();
  const headers: Record<string, string> = { "Content-Type": "application/json", ...extra };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function login(email: string, role: string = "operator", apiKey?: string): Promise<UserProfile> {
  if (isDemoMode()) {
    const user: UserProfile = {
      user_id: email,
      role: role as any,
      name: email === "admin@we-make-devs.org" ? "Lead Cloud Architect" : email === "auditor@we-make-devs.org" ? "Compliance Auditor" : "FinOps SRE Operator",
      token: `demo.jwt.${email.replace(/[^a-zA-Z0-9]/g, "")}`,
      permissions: role === "admin" ? ["view", "approve", "mutate", "admin"] : role === "operator" ? ["view", "approve", "mutate"] : ["view"],
      auth_type: apiKey ? "api_key" : "bearer",
    };
    if (typeof window !== "undefined") {
      window.localStorage.setItem("netra_user_profile", JSON.stringify(user));
      window.localStorage.setItem("netra_auth_token", user.token || "");
    }
    return user;
  }

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, role, api_key: apiKey }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  const user: UserProfile = {
    user_id: data.user.email,
    role: data.user.role,
    name: data.user.name,
    token: data.token,
    permissions: data.user.permissions,
    auth_type: "bearer",
  };
  if (typeof window !== "undefined") {
    window.localStorage.setItem("netra_user_profile", JSON.stringify(user));
    window.localStorage.setItem("netra_auth_token", data.token);
  }
  return user;
}

export function logout(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem("netra_user_profile");
    window.localStorage.removeItem("netra_auth_token");
  }
}

export async function generateApiKey(): Promise<{ ok: boolean; api_key: string; key_hash: string }> {
  if (isDemoMode()) {
    const dummyKey = `netra_live_${Math.random().toString(16).slice(2)}${Math.random().toString(16).slice(2)}`;
    return {
      ok: true,
      api_key: dummyKey,
      key_hash: `sha256_${dummyKey.slice(0, 16)}`,
    };
  }

  const res = await fetch(`${API_BASE}/auth/keys`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.error || `HTTP ${res.status}`);
  }
  return await res.json();
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
      clientSummary.approved_remediations_count = (clientSummary.approved_remediations_count || 5) + 1;
      clientSummary.multiple = Math.round((clientSummary.burn_inr_hour / clientSummary.baseline_inr_hour) * 100) / 100;
    }
    return { execution_arn: `arn:aws:states:ap-south-1:123456789012:execution:netra-remediate:${id}`, status: "EXECUTING" };
  }

  const res = await fetch(`${API_BASE}/findings/${id}/approve`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.error || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function dismissFinding(id: string): Promise<{ status: string }> {
  if (isDemoMode()) {
    const target = clientFindings.find(f => f.finding_id === id);
    if (target) target.status = "DISMISSED";
    return { status: "DISMISSED" };
  }

  const res = await fetch(`${API_BASE}/findings/${id}/dismiss`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.error || `HTTP ${res.status}`);
  }
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
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ hours }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.error || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function postRollback(auditId: string, snapshotId: string): Promise<{ ok: boolean; status: string; restored_volume_id?: string; error?: string }> {
  if (isDemoMode()) {
    const newVolId = `vol-${Math.random().toString(16).slice(2, 10)}`;
    clientAudit.unshift({
      audit_id: `AUD#${Date.now()}#ROLLBACK`,
      action: "rollback_restore",
      target_id: snapshotId,
      approved_by: "lead-architect@we-make-devs.org (Admin)",
      recovered_month_inr: -1200.0,
      timestamp: Math.floor(Date.now() / 1000),
      revert: true,
      rollback_snapshot_id: snapshotId,
    });
    return { ok: true, status: "RESTORED", restored_volume_id: newVolId };
  }

  const res = await fetch(`${API_BASE}/audit/${auditId}/rollback`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ snapshot_id: snapshotId }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.error || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function getAudit(limit: number = 50): Promise<{ entries: AuditEntry[]; recovered_month_inr: number; action_count: number; revert_count: number }> {
  if (isDemoMode()) {
    const totalRecovered = clientAudit.reduce((acc, it) => acc + (it.revert ? -Math.abs(it.recovered_month_inr) : it.recovered_month_inr), 0);
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
      revert_count: 0,
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
    narrative_source: "openai",
  };

  clientResources.unshift(runawayRes);
  clientFindings.unshift(newFinding);
  clientSummary.burn_inr_hour += 66.55;
  clientSummary.multiple = Math.round((clientSummary.burn_inr_hour / clientSummary.baseline_inr_hour) * 100) / 100;

  return { status: "simulated", finding_id: newFid };
}
