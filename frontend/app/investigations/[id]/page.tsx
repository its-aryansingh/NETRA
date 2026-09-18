"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { approveFinding, dismissFinding, getFinding, snoozeFinding } from "@/lib/api";
import { FindingItem } from "@/lib/demo-data";
import { formatAge, formatINR } from "@/lib/format";
import AgentNarrative from "@/components/AgentNarrative";
import EvidenceChips from "@/components/EvidenceChips";
import AgentTrace from "@/components/AgentTrace";
import RemediationPanel from "@/components/RemediationPanel";
import DetectionBadge from "@/components/DetectionBadge";

export default function InvestigationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [finding, setFinding] = useState<FindingItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getFinding(id);
        setFinding(data);
      } catch (err) {
        console.error("Failed to load finding:", err);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [id]);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 animate-pulse space-y-6">
        <div className="h-6 w-32 bg-[var(--surface-2)] rounded" />
        <div className="h-28 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-6">
            <div className="h-48 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
            <div className="h-32 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
            <div className="h-32 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
          </div>
          <div className="lg:col-span-4 space-y-6">
            <div className="h-96 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
          </div>
        </div>
      </div>
    );
  }

  if (!finding) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 text-center">
        <h2 className="text-xl font-display font-semibold text-[var(--text)] mb-2">
          Finding Not Found
        </h2>
        <p className="text-sm font-mono text-[var(--text-3)] mb-6">
          No finding record matches identifier {id}
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-[7px] bg-[var(--surface)] border border-[var(--line)] text-xs font-mono text-[var(--text)] hover:border-[var(--line-soft)]"
        >
          &larr; Return to Overview
        </Link>
      </div>
    );
  }

  const sevBadge = {
    critical: "bg-[var(--alarm)]/10 text-[var(--alarm)] border-[var(--alarm)]/30",
    warning: "bg-[var(--amber)]/10 text-[var(--amber)] border-[var(--amber)]/30",
    info: "bg-[var(--text-3)]/10 text-[var(--text-2)] border-[var(--line)]",
  }[finding.severity];

  const isProtected = finding.resource.tags?.["netra:protected"] !== undefined;
  const now = Math.floor(Date.now() / 1000);
  const ageSec = Math.max(0, now - finding.detected_at);
  const rawAny = finding as any;
  const latencyMs =
    rawAny.detection_latency_ms != null
      ? rawAny.detection_latency_ms
      : rawAny.detection_latency_s != null
      ? rawAny.detection_latency_s * 1000
      : null;
  const detectionPath = rawAny.detection_path || (latencyMs && latencyMs < 30000 ? "fast" : "sweep");

  const isDenied = isProtected || (rawAny.policy_decision && !rawAny.policy_decision.allowed);
  const isResolved = finding.status === "RESOLVED" || finding.status === "EXECUTING";

  const handleMobileApprove = async () => {
    if (isDenied || isResolved) return;
    setActionLoading(true);
    try {
      await approveFinding(finding.finding_id);
      setFinding({ ...finding, status: "RESOLVED" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleMobileDismiss = async () => {
    if (isResolved) return;
    setActionLoading(true);
    try {
      await dismissFinding(finding.finding_id);
      setFinding({ ...finding, status: "DISMISSED" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleMobileSnooze = async () => {
    if (isResolved) return;
    setActionLoading(true);
    try {
      await snoozeFinding(finding.finding_id, 2);
      setFinding({ ...finding, status: "SNOOZED" });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6 pb-20 max-[430px]:pb-24">
      {/* Breadcrumb Back Link */}
      <div>
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-[var(--text-3)] hover:text-[var(--text)] transition-colors"
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="m15 18-6-6 6-6" />
          </svg>
          <span>Overview</span>
          <span className="text-[var(--line-soft)]">/</span>
          <span className="text-[var(--text-2)]">{finding.finding_id}</span>
        </Link>
      </div>

      {/* Header & Two-Cell Exposure Block */}
      <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          {/* Title & Metadata */}
          <div className="space-y-2">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className={`px-2.5 py-0.5 rounded-[5px] text-xs font-mono font-bold uppercase border ${sevBadge}`}>
                {finding.severity}
              </span>
              {/* DetectionBadge placed directly next to severity badge */}
              <DetectionBadge latencyMs={latencyMs} detectionPath={detectionPath} />
              <span className="px-2.5 py-0.5 rounded-[5px] text-xs font-mono bg-[var(--surface-2)] border border-[var(--line-soft)] text-[var(--text-2)]">
                {finding.status}
              </span>
              <span className="text-xs font-mono text-[var(--text-3)]">
                Detected {formatAge(ageSec)} ago
              </span>
            </div>

            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-lg sm:text-xl font-display font-semibold text-[var(--text)]">
                {finding.headline || `${finding.resource.sub_type} spend anomaly`}
              </h1>
              {/* Fallback Chip: neutral styling beside headline when model bypassed */}
              {finding.narrative_source === "fallback" && (
                <span
                  className="inline-flex items-center px-2 py-0.5 rounded-[5px] text-[11px] font-mono bg-[var(--surface-2)] text-[var(--text-3)] border border-[var(--line-soft)]"
                  title="Deterministic arithmetic narrative without LLM invocation"
                >
                  deterministic narrative
                </span>
              )}
            </div>

            <div className="flex items-center gap-4 text-xs font-mono text-[var(--text-3)] flex-wrap">
              <span>Target: <code className="text-[var(--text)]">{finding.resource.resource_id}</code></span>
              <span>Type: <code className="text-[var(--text)]">{finding.resource.sub_type}</code></span>
              <span>Region: <code className="text-[var(--text)]">{finding.resource.region}</code></span>
              {isProtected && (
                <span className="text-[var(--amber)] bg-[var(--amber)]/10 px-1.5 py-0.5 rounded border border-[var(--amber)]/30">
                  netra:protected
                </span>
              )}
            </div>
          </div>

          {/* Two-Cell Exposure Block (moves under headline on mobile) */}
          <div className="flex items-center gap-4 border-t lg:border-t-0 lg:border-l border-[var(--line)] pt-4 lg:pt-0 lg:pl-6 max-[430px]:w-full">
            <div className="bg-[var(--surface-2)] border border-[var(--line-soft)] rounded-[10px] p-3.5 flex-1 min-w-[130px]">
              <div className="text-[11px] uppercase tracking-[0.09em] text-[var(--text-3)] font-mono mb-1">
                Burning now
              </div>
              <div className="font-mono text-xl font-semibold text-[var(--ember)]">
                {formatINR(finding.computed.inr_hour)}
                <span className="text-xs text-[var(--text-3)] font-normal">/hr</span>
              </div>
              <div className="text-[10px] font-mono text-[var(--text-3)] mt-0.5">
                {finding.computed.multiple}× baseline
              </div>
            </div>

            <div className="bg-[var(--surface-2)] border border-[var(--line-soft)] rounded-[10px] p-3.5 flex-1 min-w-[130px]">
              <div className="text-[11px] uppercase tracking-[0.09em] text-[var(--text-3)] font-mono mb-1">
                30-day exposure
              </div>
              <div className="font-mono text-xl font-semibold text-[var(--alarm)]">
                {formatINR(finding.computed.inr_month)}
              </div>
              <div className="text-[10px] font-mono text-[var(--text-3)] mt-0.5">
                {finding.computed.runway_hours}h credit runway
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid: Narrative & Evidence (8 cols) + Remediation (4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Analysis, Observability, Execution Trace */}
        <div className="lg:col-span-8 space-y-6">
          {/* Agent Narrative with Deterministic Badge Support */}
          {finding.narrative && (
            <AgentNarrative
              paragraphs={finding.narrative.narrative}
              narrativeSource={finding.narrative_source || "bedrock"}
            />
          )}

          {/* Supporting Evidence Chips */}
          {finding.narrative?.evidence && (
            <EvidenceChips evidence={finding.narrative.evidence} />
          )}

          {/* Strands OpenTelemetry Agent Trace with Trust Boundary divider */}
          <AgentTrace traces={finding.agent_trace || []} />
        </div>

        {/* Right Column: Remediation Actions & Fired Rules */}
        <div className="lg:col-span-4 space-y-6">
          <RemediationPanel
            findingId={finding.finding_id}
            resourceId={finding.resource.resource_id}
            recommendedAction={finding.narrative?.recommended_action || "stop"}
            recoveredMonthInr={finding.computed.inr_month}
            risk={finding.narrative?.risk || "medium"}
            steps={finding.narrative?.steps || []}
            rulesFired={finding.rules_fired || []}
            status={finding.status}
            isProtected={isProtected}
            policyDecision={rawAny.policy_decision}
            onStatusChange={(newStatus) => {
              setFinding({ ...finding, status: newStatus as FindingItem["status"] });
            }}
          />
        </div>
      </div>

      {/* Mobile Sticky Action Bar for screens <= 430px */}
      <div className="max-[430px]:flex hidden fixed bottom-0 left-0 right-0 z-50 bg-[var(--surface-2)]/95 backdrop-blur border-t border-[var(--line)] px-3 py-2 h-14 items-center justify-between gap-2 shadow-2xl">
        {isResolved ? (
          <div className="w-full text-center text-xs font-mono font-semibold text-[var(--mint)]">
            ✓ Remediated
          </div>
        ) : isDenied ? (
          <div className="flex-1 text-[11px] font-mono text-[var(--alarm)] font-semibold truncate">
            Policy denial: {rawAny.policy_decision?.rule_id || (isProtected ? "forbid_protected" : "forbid")}
          </div>
        ) : (
          <button
            onClick={handleMobileApprove}
            disabled={actionLoading}
            className="flex-1 min-h-[38px] px-3 rounded-[7px] bg-[var(--ember)] text-[var(--ground)] font-semibold text-xs uppercase font-mono tracking-wider transition-colors"
          >
            {actionLoading ? "..." : "Approve"}
          </button>
        )}

        <button
          onClick={handleMobileSnooze}
          disabled={actionLoading || isResolved}
          className="min-h-[38px] px-3 rounded-[7px] bg-[var(--surface)] text-[var(--text-2)] text-xs font-mono border border-[var(--line)]"
        >
          Snooze
        </button>

        <button
          onClick={handleMobileDismiss}
          disabled={actionLoading || isResolved}
          className="min-h-[38px] px-3 rounded-[7px] bg-[var(--surface)] text-[var(--text-3)] text-xs font-mono border border-[var(--line)]"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
