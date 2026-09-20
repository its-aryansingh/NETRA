"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getAudit, getAuditByCause } from "@/lib/api";
import { AuditEntry } from "@/lib/demo-data";
import { formatINR } from "@/lib/format";
import AuditLedger from "@/components/AuditLedger";
import { CauseBars } from "@/components/CauseBars";

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [causes, setCauses] = useState<Array<{ label: string; amount_inr: number; count: number }>>([]);
  const [recoveredTotal, setRecoveredTotal] = useState<number>(0);
  const [actionCount, setActionCount] = useState<number>(0);
  const [revertCount, setRevertCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);

  const refreshAudit = async () => {
    try {
      const [auditRes, causeRes] = await Promise.all([
        getAudit(50),
        getAuditByCause(),
      ]);
      setEntries(auditRes.entries || []);
      setRecoveredTotal(auditRes.recovered_month_inr || 0);
      setActionCount(auditRes.action_count || 0);
      setRevertCount(auditRes.revert_count || 0);
      setCauses(causeRes.causes || []);
    } catch (err) {
      console.error("Failed to load audit data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshAudit();
  }, []);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 animate-pulse space-y-6">
        <div className="h-6 w-32 bg-[var(--surface-2)] rounded" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-32 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
          <div className="h-32 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
          <div className="h-32 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
        </div>
        <div className="h-64 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
        <div className="h-96 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Breadcrumb Navigation */}
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
          <span className="text-[var(--text-2)]">Remediation Audit</span>
        </Link>
      </div>

      {/* Header Summary Tiles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Recovered Total in Mint */}
        <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-wider text-[var(--text-3)] font-mono">
              Recovered this month
            </span>
            <span className="px-2 py-0.5 rounded-[5px] text-[10px] font-mono bg-[var(--mint-bg)] text-[var(--mint)] border border-[var(--mint-line)] font-semibold">
              Verified
            </span>
          </div>
          <div className="font-mono text-3xl sm:text-4xl font-semibold text-[var(--mint)] my-2">
            {formatINR(recoveredTotal)}
          </div>
          <div className="text-xs text-[var(--text-3)] font-mono">
            Approved remediations
          </div>
        </div>

        {/* Executed Remediations Tile */}
        <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-wider text-[var(--text-3)] font-mono">
              Executed actions
            </span>
            <span className="px-2 py-0.5 rounded-[5px] text-[10px] font-mono bg-[var(--surface-2)] text-[var(--text-2)] border border-[var(--line-soft)]">
              Human-Authorized
            </span>
          </div>
          <div className="font-mono text-3xl sm:text-4xl font-semibold text-[var(--text)] my-2">
            {actionCount}
          </div>
          <div className="text-xs text-[var(--text-3)] font-mono">
            Stopped, terminated, or deleted
          </div>
        </div>

        {/* Rollback Reverts Tile */}
        <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-wider text-[var(--text-3)] font-mono">
              Rollbacks / reverts
            </span>
            <span className="px-2 py-0.5 rounded-[5px] text-[10px] font-mono bg-[var(--surface-2)] text-[var(--text-2)] border border-[var(--line-soft)]">
              Safety Net
            </span>
          </div>
          <div className="font-mono text-3xl sm:text-4xl font-semibold text-[var(--amber)] my-2">
            {revertCount}
          </div>
          <div className="text-xs text-[var(--text-3)] font-mono">
            7-day snapshot retention
          </div>
        </div>
      </div>

      {/* Recovered by Cause Horizontal Bar Chart */}
      <CauseBars causes={causes} />

      {/* Immutable Append-Only Remediation Ledger */}
      <AuditLedger entries={entries} onRollbackSuccess={refreshAudit} />
    </div>
  );
}
