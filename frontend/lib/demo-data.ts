/**
 * Realistic deterministic demo fixtures for NETRA dashboard.
 * Active when NEXT_PUBLIC_DEMO=1 or demo mode is toggled.
 */

export interface PricedResourceItem {
  resource_id: string;
  kind: "ec2" | "ebs" | "nat";
  sub_type: string;
  region: string;
  launched_at: number;
  age_seconds: number;
  usd_hour: number;
  inr_hour: number;
  price_ref: string;
  tags: Record<string, string | null>;
  state: string;
  meta: Record<string, any>;
  util?: string;
  history?: number[];
}

export interface FindingItem {
  finding_id: string;
  severity: "critical" | "warning" | "info";
  status: "DETECTED" | "NARRATING" | "AWAITING_APPROVAL" | "EXECUTING" | "RESOLVED" | "DISMISSED" | "SNOOZED";
  rules_fired: Array<{ rule: string; detail: string }>;
  resource: PricedResourceItem;
  computed: {
    inr_hour: number;
    inr_month: number;
    baseline_inr_hour: number;
    multiple: number;
    runway_hours: number;
    share_of_burn_pct: number;
  };
  detected_at: number;
  headline?: string;
  narrative?: {
    headline: string;
    narrative: string[];
    evidence: Array<{ label: string; value: string }>;
    recommended_action: string;
    risk: "low" | "medium" | "high";
    steps: Array<{ api: string; why: string }>;
  };
  agent_trace?: Array<{ tool: string; ms: number; span_id?: string }>;
  narrative_source?: "openai" | "bedrock" | "ollama" | "fallback";
}

export interface AuditEntry {
  audit_id: string;
  action: string;
  target_id: string;
  approved_by: string;
  recovered_month_inr: number;
  timestamp: number;
  rollback_snapshot_id?: string;
  revert?: boolean;
}

const NOW = Math.floor(Date.now() / 1000);

export const DEMO_SUMMARY = {
  burn_inr_hour: 412.80,
  baseline_inr_hour: 23.04,
  multiple: 17.92,
  projected_month_inr: 301344.0,
  credits_initial_usd: 200.0,
  credits_remaining_usd: 161.40,
  runway_hours: 14.9,
  prevented_today_inr: 71921.8,
  approved_remediations_count: 5,
  collector_age_s: 8,
  usd_inr: 88.50,
  verified_prices: 5,
  total_prices: 5,
  reported: {
    inr_hour: 18.40,
    usd_hour: 0.2079,
    as_of_epoch: NOW - 50400,
    staleness_seconds: 50400,
    granularity: "HOURLY" as const,
    available: true,
    reason: null,
  },
};

// 24h burn series with a sharp step change at t - 41 min
export const DEMO_BURN_SERIES = (() => {
  const points = [];
  const start = NOW - 24 * 3600;
  const stepTime = NOW - 41 * 60;

  for (let t = start; t <= NOW; t += 1800) {
    let burn = 23.04;
    // slight jitter around baseline
    const jitter = Math.sin(t / 7200) * 0.4;
    burn += jitter;

    if (t >= stepTime) {
      burn += 104.26; // jump up to ~127.30 INR/hr
    }

    points.push({
      ts: t,
      inr_hour: Math.round(burn * 100) / 100,
    });
  }
  return {
    points,
    baseline_inr_hour: 23.04,
    step_at_ts: stepTime,
  };
})();

export const DEMO_RESOURCES: PricedResourceItem[] = [
  {
    resource_id: "i-0a4f39c7b12e8d5a1",
    kind: "ec2",
    sub_type: "c5.4xlarge",
    region: "ap-south-1",
    launched_at: NOW - 2460, // 41m ago
    age_seconds: 2460,
    usd_hour: 0.752,
    inr_hour: 66.55,
    price_ref: "sha256:4a9f13c8b417e290fbb69411bc294a0293da27f8cf28e1c6b891823abce1283a",
    tags: { Owner: null, "netra:protected": null },
    state: "running",
    meta: { vpc_id: "vpc-0a1b2c3d", subnet_id: "subnet-09f1a", root_device: "/dev/xvda" },
    util: "2.0%",
    history: [0, 0, 0, 0, 0, 0, 0, 0, 15.0, 42.5, 66.55, 66.55, 66.55, 66.55, 66.55, 66.55, 66.55, 66.55, 66.55, 66.55, 66.55, 66.55, 66.55, 66.55],
  },
  {
    resource_id: "i-0prodapp000000001",
    kind: "ec2",
    sub_type: "m5.xlarge",
    region: "ap-south-1",
    launched_at: NOW - 14 * 86400,
    age_seconds: 14 * 86400,
    usd_hour: 0.212,
    inr_hour: 18.76,
    price_ref: "sha256:1a82bc12948eefb9281729daebc1092834710293847102938471029384710293",
    tags: { Owner: "team-core", Environment: "production" },
    state: "running",
    meta: { vpc_id: "vpc-0a1b2c3d", subnet_id: "subnet-09f1a" },
    util: "48.2%",
    history: [18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76, 18.76],
  },
  {
    resource_id: "i-0protected9999999",
    kind: "ec2",
    sub_type: "c5.2xlarge",
    region: "ap-south-1",
    launched_at: NOW - 2 * 86400,
    age_seconds: 2 * 86400,
    usd_hour: 0.376,
    inr_hour: 33.28,
    price_ref: "sha256:39bf901238471092834710293847102938471029384710293847102938471029",
    tags: { Owner: "lead-architect", "netra:protected": "true" },
    state: "running",
    meta: { vpc_id: "vpc-0a1b2c3d" },
    util: "1.5%",
    history: [33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28, 33.28],
  },
  {
    resource_id: "vol-0987654321fedcba0",
    kind: "ebs",
    sub_type: "gp3",
    region: "ap-south-1",
    launched_at: NOW - 4041,
    age_seconds: 4041,
    usd_hour: 0.0424,
    inr_hour: 3.75,
    price_ref: "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    tags: { Owner: "data-ml", "netra:protected": null },
    state: "available",
    meta: { size_gb: 340, iops: 3000, throughput: 125 },
    util: "0 IOPS",
    history: [3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75],
  },
  {
    resource_id: "nat-0123456789abcdef0",
    kind: "nat",
    sub_type: "nat",
    region: "ap-south-1",
    launched_at: NOW - 8 * 86400,
    age_seconds: 8 * 86400,
    usd_hour: 0.056,
    inr_hour: 4.96,
    price_ref: "sha256:8871928374019283740192837401928374019283740192837401928374019283",
    tags: { Owner: "infra", "netra:protected": null },
    state: "available",
    meta: { vpc_id: "vpc-0a1b2c3d", subnet_id: "subnet-09f1a" },
    util: "0.1 KB/s",
    history: [4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96, 4.96],
  },
];

export const DEMO_FINDINGS: FindingItem[] = [
  {
    finding_id: "01J8ABCDEF1234567890123456",
    severity: "critical",
    status: "AWAITING_APPROVAL",
    rules_fired: [
      { rule: "idle_compute", detail: "cpu_max=2.0% age=41m" },
      { rule: "burn_step_change", detail: "total_inr_hour=127.30 baseline=23.04 multiple=5.53" },
    ],
    resource: DEMO_RESOURCES[0],
    computed: {
      inr_hour: 66.55,
      inr_month: 48576.0,
      baseline_inr_hour: 23.04,
      multiple: 3.89,
      runway_hours: 14.9,
      share_of_burn_pct: 94.4,
    },
    detected_at: NOW - 2460,
    headline: "Runaway c5.4xlarge (₹66.55/hr) burning 3.9× baseline",
    narrative: {
      headline: "Runaway c5.4xlarge (₹66.55/hr) burning 3.9× baseline",
      narrative: [
        "A c5.4xlarge has been running in ap-south-1 for 41 minutes. It is costing ₹66.55 per hour — 3.9× your usual baseline — and accounts for 94.4% of everything you are currently spending.",
        "CloudWatch metrics report CPU utilization at 2.0% with negligible network traffic (450 packets out). The compute instance has remained idle since launch with no active user workload.",
        "Projected 30-day exposure is ₹48576.0 with an estimated credit runway of 14.9 hours. We recommend snapshotting the root volume and terminating the instance to prevent credit exhaustion.",
      ],
      evidence: [
        {"label": "CPUUtilization max", "value": "2.0%"},
        {"label": "NetworkPacketsOut", "value": "450"},
        {"label": "State", "value": "running"},
        {"label": "Active Dependents", "value": "0"},
        {"label": "Root Volume", "value": "30 GB xvda"},
        {"label": "Price Source", "value": "AWS Price List (SHA-256 verified)"},
      ],
      recommended_action: "snapshot_and_terminate",
      risk: "medium",
      steps: [
        {"api": "ec2:CreateSnapshot", "why": "Safeguard root volume before termination"},
        {"api": "ec2:TerminateInstances", "why": "Terminate runaway compute instance"},
      ],
    },
    agent_trace: [
      { tool: "get_finding", ms: 4, span_id: "span-01a" },
      { tool: "get_resource_details", ms: 48, span_id: "span-02b" },
      { tool: "get_cloudwatch_utilization", ms: 112, span_id: "span-03c" },
      { tool: "find_dependents", ms: 36, span_id: "span-04d" },
      { tool: "model_converse (OpenAI gpt-4o-mini)", ms: 412, span_id: "span-05e" },
    ],
    narrative_source: "openai",
  },
  {
    finding_id: "01J8ORPHANEDB0000000000001",
    severity: "warning",
    status: "AWAITING_APPROVAL",
    rules_fired: [
      { rule: "orphaned_storage", detail: "unattached size_gb=340 age=67m" },
    ],
    resource: DEMO_RESOURCES[3],
    computed: {
      inr_hour: 3.75,
      inr_month: 2737.5,
      baseline_inr_hour: 23.04,
      multiple: 1.0,
      runway_hours: 999.9,
      share_of_burn_pct: 2.9,
    },
    detected_at: NOW - 4041,
    headline: "Orphaned 340 GB gp3 volume unattached for 67 minutes",
    narrative: {
      headline: "Orphaned 340 GB gp3 volume unattached for 67 minutes",
      narrative: [
        "An unattached gp3 storage volume has been idle in ap-south-1 for 67 minutes. It is costing ₹3.75 per hour without active attachments.",
        "Volume metrics indicate 0 read/write IOPS since detachment from predecessor compute instance.",
        "Projected 30-day exposure is ₹2737.5. We recommend archiving data with a snapshot and deleting the detached volume.",
      ],
      evidence: [
        {"label": "Volume Size", "value": "340 GB"},
        {"label": "Volume Type", "value": "gp3"},
        {"label": "Status", "value": "available"},
        {"label": "Active Attachments", "value": "0"},
      ],
      recommended_action: "snapshot_and_delete",
      risk: "low",
      steps: [
        {"api": "ec2:CreateSnapshot", "why": "Archive volume data"},
        {"api": "ec2:DeleteVolume", "why": "Delete orphaned volume"},
      ],
    },
    agent_trace: [
      { tool: "get_finding", ms: 3 },
      { tool: "get_resource_details", ms: 32 },
      { tool: "find_dependents", ms: 21 },
      { tool: "templated_narrative", ms: 1 },
    ],
    narrative_source: "fallback",
  },
  {
    finding_id: "01J8PROTECTED1234567890123",
    severity: "info",
    status: "AWAITING_APPROVAL",
    rules_fired: [
      { rule: "idle_compute", detail: "cpu_max=1.5% age=48h" },
    ],
    resource: DEMO_RESOURCES[2],
    computed: {
      inr_hour: 33.28,
      inr_month: 24294.4,
      baseline_inr_hour: 23.04,
      multiple: 1.4,
      runway_hours: 45.2,
      share_of_burn_pct: 26.1,
    },
    detected_at: NOW - 3600,
    headline: "Protected c5.2xlarge idle: remediation blocked by netra:protected",
    narrative: {
      headline: "Protected c5.2xlarge idle: remediation blocked by netra:protected",
      narrative: [
        "A c5.2xlarge compute instance has run with minimal utilization. It is burning ₹33.28 per hour.",
        "Although utilization is below 1.5%, the resource carries the netra:protected tag.",
        "Because this resource is marked protected, automated remediation is blocked. Contact lead-architect for review.",
      ],
      evidence: [
        {"label": "Protection Tag", "value": "netra:protected=true"},
        {"label": "Owner", "value": "lead-architect"},
        {"label": "CPUUtilization max", "value": "1.5%"},
      ],
      recommended_action: "none",
      risk: "low",
      steps: [
        {"api": "none", "why": "Resource is protected; no mutating actions permitted"},
      ],
    },
    agent_trace: [
      { tool: "get_finding", ms: 2 },
      { tool: "get_resource_details", ms: 38 },
      { tool: "model_converse", ms: 380 },
    ],
    narrative_source: "openai",
  },
];

export const DEMO_AUDIT_LOG: AuditEntry[] = [
  {
    audit_id: "AUD#1789740000000#01J8A",
    action: "terminate",
    target_id: "i-098e721a6c54b3d1f",
    approved_by: "student-dev@we-make-devs.org",
    recovered_month_inr: 48576.0,
    timestamp: NOW - 7200,
    rollback_snapshot_id: "snap-0a98f123bc",
  },
  {
    audit_id: "AUD#1789736400000#01J8B",
    action: "delete",
    target_id: "vol-0123456789abcdef0",
    approved_by: "student-dev@we-make-devs.org",
    recovered_month_inr: 3620.8,
    timestamp: NOW - 10800,
    rollback_snapshot_id: "snap-0fedcba987",
  },
  {
    audit_id: "AUD#1789732800000#01J8C",
    action: "delete",
    target_id: "nat-0idle000000000001",
    approved_by: "student-dev@we-make-devs.org",
    recovered_month_inr: 4070.4,
    timestamp: NOW - 14400,
  },
  {
    audit_id: "AUD#1789729200000#01J8D",
    action: "stop",
    target_id: "i-0stagingcluster123",
    approved_by: "admin@bharatbuilds.dev",
    recovered_month_inr: 13829.6,
    timestamp: NOW - 28800,
  },
  {
    audit_id: "AUD#1789725600000#01J8E",
    action: "delete",
    target_id: "vol-0orphanedtemp123",
    approved_by: "admin@bharatbuilds.dev",
    recovered_month_inr: 1825.0,
    timestamp: NOW - 43200,
    rollback_snapshot_id: "snap-0temp12345",
  },
];

export const DEMO_BY_CAUSE = [
  { label: "idle_compute", amount_inr: 62405.6, count: 2 },
  { label: "orphaned_storage", amount_inr: 5445.8, count: 2 },
  { label: "idle_nat", amount_inr: 4070.4, count: 1 },
];
