import { formatDate, formatINR } from "@/lib/format";
import { AuditEntry } from "@/lib/demo-data";

interface AuditLedgerProps {
  entries: AuditEntry[];
}

export default function AuditLedger({ entries }: AuditLedgerProps) {
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
                      {entry.rollback_snapshot_id ? (
                        <span className="inline-flex items-center gap-1 text-[var(--text-2)]">
                          <svg className="w-3 h-3 text-[var(--mint)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                            <path d="M3 3v5h5" />
                          </svg>
                          <span>{entry.rollback_snapshot_id}</span>
                        </span>
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
