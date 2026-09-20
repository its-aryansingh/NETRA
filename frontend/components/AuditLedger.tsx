"use client";

import { useState } from "react";
import { formatDate, formatINR } from "@/lib/format";
import { AuditEntry } from "@/lib/demo-data";
import { postRollback, getCurrentUser } from "@/lib/api";

interface AuditLedgerProps {
  entries: AuditEntry[];
  onRollbackSuccess?: () => void;
}

export default function AuditLedger({ entries, onRollbackSuccess }: AuditLedgerProps) {
  const [inFlightId, setInFlightId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const handleRollback = async (entry: AuditEntry) => {
    if (!entry.rollback_snapshot_id) return;
    const user = getCurrentUser();
    if (user && user.role !== "admin") {
      setFeedback({
        type: "error",
        message: `403 Forbidden: Only Admin role can trigger EBS rollback restoration (Current role: ${user.role}). Switch persona in TopBar to Admin to execute rollbacks.`,
      });
      return;
    }

    try {
      setInFlightId(entry.audit_id);
      setFeedback(null);
      const res = await postRollback(entry.audit_id, entry.rollback_snapshot_id);
      setFeedback({
        type: "success",
        message: `Restoration triggered for ${entry.target_id}! Restored volume: ${res.restored_volume_id || "vol-safeguard-ok"} (${res.status})`,
      });
      if (onRollbackSuccess) onRollbackSuccess();
    } catch (err: any) {
      setFeedback({
        type: "error",
        message: err?.message || "Rollback execution failed",
      });
    } finally {
      setInFlightId(null);
    }
  };

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--text)] font-display">
            Append-Only Remediation Ledger
          </h3>
          <p className="text-xs text-[var(--text-3)] font-mono">
            Every remediation audited with authorized principal and rollback snapshot
          </p>
        </div>

        {/* Lock Chip */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-[7px] bg-[var(--surface-2)] border border-[var(--line-soft)] text-xs font-mono text-[var(--text-3)]">
          <svg className="w-3.5 h-3.5 text-[var(--mint)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <span>append-only · DynamoDB stream</span>
        </div>
      </div>

      {feedback && (
        <div
          className={`mb-4 px-3 py-2 rounded-[8px] text-xs font-mono flex items-center justify-between border ${
            feedback.type === "success"
              ? "bg-[var(--mint-bg)] text-[var(--mint)] border-[var(--mint-line)]"
              : "bg-[var(--alarm)]/10 text-[var(--alarm)] border-[var(--alarm)]/30"
          }`}
        >
          <span>{feedback.message}</span>
          <button onClick={() => setFeedback(null)} className="ml-2 hover:opacity-75 font-bold">×</button>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-[var(--line)] text-[var(--text-3)] uppercase tracking-wider text-[11px]">
              <th className="pb-3 font-medium">When</th>
              <th className="pb-3 font-medium">Action</th>
              <th className="pb-3 font-medium">Target Resource</th>
              <th className="pb-3 font-medium">Approved By</th>
              <th className="pb-3 font-medium text-right">Recovered</th>
              <th className="pb-3 font-medium pl-4">Rollback Snapshot</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--line-soft)]">
            {entries.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-[var(--text-3)]">
                  No remediations recorded yet.
                </td>
              </tr>
            ) : (
              entries.map(entry => {
                const isRevert = entry.revert || entry.recovered_month_inr < 0;
                const canRollback = Boolean(entry.rollback_snapshot_id && entry.rollback_snapshot_id !== "none" && !isRevert);
                return (
                  <tr key={entry.audit_id} className="hover:bg-[var(--surface-2)]/50 transition-colors">
                    <td className="py-3 text-[var(--text-3)]">{formatDate(entry.timestamp)}</td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded-[5px] text-[10px] uppercase font-bold border ${
                        entry.action === "terminate"
                          ? "bg-[var(--alarm)]/10 text-[var(--alarm)] border-[var(--alarm)]/20"
                          : entry.action === "stop"
                          ? "bg-[var(--amber)]/10 text-[var(--amber)] border-[var(--amber)]/20"
                          : isRevert
                          ? "bg-[var(--alarm)]/20 text-[var(--alarm)] border-[var(--alarm)]/30"
                          : "bg-[var(--surface-2)] text-[var(--text-2)] border-[var(--line)]"
                      }`}>
                        {entry.action}
                      </span>
                    </td>
                    <td className="py-3 text-[var(--text)] font-semibold">{entry.target_id}</td>
                    <td className="py-3 text-[var(--text-2)]">{entry.approved_by}</td>
                    <td className={`py-3 text-right font-semibold ${isRevert ? "text-[var(--alarm)]" : "text-[var(--mint)]"}`}>
                      {isRevert ? "-" : "+"}{formatINR(Math.abs(entry.recovered_month_inr))}
                      <span className="text-[10px] text-[var(--text-3)] font-normal ml-0.5">/mo</span>
                    </td>
                    <td className="py-3 pl-4 text-[var(--text-3)]">
                      {entry.rollback_snapshot_id && entry.rollback_snapshot_id !== "none" ? (
                        <div className="inline-flex items-center gap-2">
                          <span className="inline-flex items-center gap-1 text-[var(--text-2)]">
                            <svg className="w-3 h-3 text-[var(--mint)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                              <path d="M3 3v5h5" />
                            </svg>
                            <span>{entry.rollback_snapshot_id}</span>
                          </span>
                          {canRollback && (
                            <button
                              onClick={() => handleRollback(entry)}
                              disabled={inFlightId === entry.audit_id}
                              className="px-2 py-0.5 rounded-[5px] text-[10px] uppercase font-semibold bg-[var(--surface-2)] hover:bg-[var(--ground)] border border-[var(--line-soft)] hover:border-[var(--line-high)] text-[var(--mint)] transition-all disabled:opacity-50"
                              title="Trigger 1-click snapshot restore (Requires Admin role)"
                            >
                              {inFlightId === entry.audit_id ? "Restoring..." : "Restore"}
                            </button>
                          )}
                        </div>
                      ) : (
                        <span>—</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
