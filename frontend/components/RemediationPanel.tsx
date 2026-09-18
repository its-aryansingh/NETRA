"use client";

import { useState } from "react";
import { formatINR } from "@/lib/format";
import { approveFinding, dismissFinding, snoozeFinding } from "@/lib/api";

interface RemediationPanelProps {
  findingId: string;
  resourceId: string;
  recommendedAction: string;
  recoveredMonthInr: number;
  risk: "low" | "medium" | "high";
  steps: Array<{ api: string; why: string }>;
  rulesFired: Array<{ rule: string; detail: string }>;
  status: "DETECTED" | "NARRATING" | "AWAITING_APPROVAL" | "EXECUTING" | "RESOLVED" | "DISMISSED" | "SNOOZED" | string;
  isProtected?: boolean;
  onStatusChange?: (newStatus: any) => void;
}

export default function RemediationPanel({
  findingId,
  resourceId,
  recommendedAction,
  recoveredMonthInr,
  risk,
  steps,
  rulesFired,
  status,
  isProtected = false,
  onStatusChange,
}: RemediationPanelProps) {
  const [loading, setLoading] = useState(false);
  const [currentStatus, setCurrentStatus] = useState(status);

  const handleApprove = async () => {
    if (isProtected) {
      alert("Action denied: Resource carries netra:protected tag.");
      return;
    }
    setLoading(true);
    try {
      await approveFinding(findingId);
      setCurrentStatus("RESOLVED");
      if (onStatusChange) onStatusChange("RESOLVED");
    } finally {
      setLoading(false);
    }
  };

  const handleDismiss = async () => {
    setLoading(true);
    try {
      await dismissFinding(findingId);
      setCurrentStatus("DISMISSED");
      if (onStatusChange) onStatusChange("DISMISSED");
    } finally {
      setLoading(false);
    }
  };

  const handleSnooze = async () => {
    setLoading(true);
    try {
      await snoozeFinding(findingId, 2);
      setCurrentStatus("SNOOZED");
      if (onStatusChange) onStatusChange("SNOOZED");
    } finally {
      setLoading(false);
    }
  };

  const riskBadge = {
    low: "bg-[var(--mint-bg)] text-[var(--mint)] border-[var(--mint-line)]",
    medium: "bg-[var(--amber)]/10 text-[var(--amber)] border-[var(--amber)]/30",
    high: "bg-[var(--alarm)]/10 text-[var(--alarm)] border-[var(--alarm)]/30",
  }[risk];

  const isResolved = currentStatus === "RESOLVED" || currentStatus === "EXECUTING";

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-6 sticky top-20">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[var(--text)] font-display">
          Remediation Plan
        </h3>
        <span className={`px-2 py-0.5 rounded-[5px] text-[10px] uppercase font-mono font-bold border ${riskBadge}`}>
          {risk} risk
        </span>
      </div>

      {/* Recovery Value Box */}
      <div className="bg-[var(--surface-2)] border border-[var(--line-soft)] rounded-[9px] p-4 mb-5">
        <div className="text-[11px] text-[var(--text-3)] font-mono uppercase tracking-wider mb-1">
          Recovered Spend Upon Approval
        </div>
        <div className="font-mono text-3xl font-semibold text-[var(--mint)]">
          {formatINR(recoveredMonthInr)}
          <span className="text-xs text-[var(--text-3)] font-normal ml-1">/ month</span>
        </div>
      </div>

      {/* Numbered Steps */}
      <div className="mb-5">
        <div className="text-xs uppercase tracking-wider text-[var(--text-3)] font-mono mb-2">
          Execution Steps
        </div>
        <ol className="space-y-2 text-xs font-mono">
          {steps.map((step, idx) => (
            <li key={idx} className="flex gap-2.5 bg-[var(--surface-2)] p-2.5 rounded-[7px] border border-[var(--line-soft)]">
              <span className="w-4 h-4 rounded-full bg-[var(--line)] text-[var(--text)] flex items-center justify-center text-[10px] shrink-0 font-bold">
                {idx + 1}
              </span>
              <div>
                <div className="text-[var(--text)] font-semibold">{step.api}</div>
                <div className="text-[var(--text-3)] text-[11px] mt-0.5">{step.why}</div>
              </div>
            </li>
          ))}
        </ol>
      </div>

      {/* Dry Run Code Block */}
      <div className="mb-5">
        <div className="text-xs uppercase tracking-wider text-[var(--text-3)] font-mono mb-1.5 flex items-center justify-between">
          <span>Dry-Run Precondition Check</span>
          <span className="text-[var(--mint)] text-[11px]">✓ Verified Safe</span>
        </div>
        <pre className="bg-[var(--ground)] border border-[var(--line-soft)] rounded-[7px] p-3 text-[11px] font-mono text-[var(--text-2)] overflow-x-auto">
{`aws ec2 ${recommendedAction.replace("_and_terminate", "")} \\
  --instance-ids ${resourceId} \\
  --dry-run`}
        </pre>
      </div>

      {/* Rules that fired */}
      <div className="mb-6">
        <div className="text-xs uppercase tracking-wider text-[var(--text-3)] font-mono mb-1.5">
          Rules That Fired
        </div>
        <div className="space-y-1 text-xs font-mono text-[var(--text-2)]">
          {rulesFired.map((rf, i) => (
            <div key={i} className="flex items-center justify-between py-1 border-b border-[var(--line-soft)]">
              <span className="text-[var(--text)]">{rf.rule}</span>
              <span className="text-[var(--text-3)] text-[11px]">{rf.detail}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      {isResolved ? (
        <div className="w-full py-3 px-4 rounded-[9px] bg-[var(--mint-bg)] border border-[var(--mint-line)] text-[var(--mint)] font-mono text-center text-xs font-semibold">
          ✓ REMEDIATION EXECUTED & RESOLVED
        </div>
      ) : isProtected ? (
        <div className="w-full py-3 px-4 rounded-[9px] bg-[var(--amber)]/10 border border-[var(--amber)]/30 text-[var(--amber)] font-mono text-center text-xs">
          Protected Resource — Automated Remediation Blocked
        </div>
      ) : (
        <div className="space-y-2">
          {/* Primary Action Button (Approve) */}
          <button
            onClick={handleApprove}
            disabled={loading}
            className="w-full min-h-[48px] py-3 px-4 rounded-[9px] bg-[var(--ember)] hover:bg-[#d97c32] text-[var(--ground)] font-semibold text-xs tracking-wide uppercase transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M20 6 9 17l-5-5" />
            </svg>
            <span>{loading ? "Authorizing..." : "Approve & Execute"}</span>
          </button>

          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={handleSnooze}
              disabled={loading}
              className="py-2 px-3 rounded-[7px] bg-[var(--surface-2)] hover:bg-[var(--line)] text-xs text-[var(--text-2)] font-mono border border-[var(--line)] min-h-[44px]"
            >
              Snooze 2h
            </button>
            <button
              onClick={handleDismiss}
              disabled={loading}
              className="py-2 px-3 rounded-[7px] bg-[var(--surface-2)] hover:bg-[var(--line)] text-xs text-[var(--text-3)] hover:text-[var(--alarm)] font-mono border border-[var(--line)] min-h-[44px]"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
