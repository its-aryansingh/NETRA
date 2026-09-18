"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { getFinding } from "@/lib/api";
import { FindingItem } from "@/lib/demo-data";
import { formatAge, formatINR } from "@/lib/format";
import AgentNarrative from "@/components/AgentNarrative";
import EvidenceChips from "@/components/EvidenceChips";
import AgentTrace from "@/components/AgentTrace";
import RemediationPanel from "@/components/RemediationPanel";

export default function InvestigationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [finding, setFinding] = useState<FindingItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);

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

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
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
              <span className="px-2.5 py-0.5 rounded-[5px] text-xs font-mono bg-[var(--surface-2)] border border-[var(--line-soft)] text-[var(--text-2)]">
                {finding.status}
              </span>
              <span className="text-xs font-mono text-[var(--text-3)]">
                Detected {formatAge(ageSec)} ago
              </span>
            </div>

            <h1 className="text-lg sm:text-xl font-display font-semibold text-[var(--text)]">
              {finding.headline || `${finding.resource.sub_type} spend anomaly`}
            </h1>

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

          {/* Two-Cell Exposure Block */}
          <div className="flex items-center gap-4 border-t lg:border-t-0 lg:border-l border-[var(--line)] pt-4 lg:pt-0 lg:pl-6">
            <div className="bg-[var(--surface-2)] border border-[var(--line-soft)] rounded-[10px] p-3.5 min-w-[140px]">
              <div className="text-[11px] uppercase tracking-wider text-[var(--text-3)] font-mono mb-1">
                Burning Now
              </div>
              <div className="font-mono text-xl font-semibold text-[var(--ember)]">
                {formatINR(finding.computed.inr_hour)}
                <span className="text-xs text-[var(--text-3)] font-normal">/hr</span>
              </div>
              <div className="text-[10px] font-mono text-[var(--text-3)] mt-0.5">
                {finding.computed.multiple}× baseline
              </div>
            </div>

            <div className="bg-[var(--surface-2)] border border-[var(--line-soft)] rounded-[10px] p-3.5 min-w-[150px]">
              <div className="text-[11px] uppercase tracking-wider text-[var(--text-3)] font-mono mb-1">
                30-Day Exposure
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

          {/* Strands OpenTelemetry Agent Trace with Proportional Mint Bars */}
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
            onStatusChange={(newStatus) => {
              setFinding({ ...finding, status: newStatus as FindingItem["status"] });
            }}
          />
        </div>
      </div>
    </div>
  );
}
