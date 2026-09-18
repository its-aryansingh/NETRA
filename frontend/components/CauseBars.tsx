"use client";

import React from "react";
import { formatINR } from "../lib/format";

interface CauseItem {
  label: string;
  amount_inr: number;
  count: number;
}

interface CauseBarsProps {
  causes: CauseItem[];
}

export const CauseBars: React.FC<CauseBarsProps> = ({ causes }) => {
  const maxAmount = Math.max(...causes.map((c) => c.amount_inr), 1);

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[12px] p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-['Familjen_Grotesk'] text-base font-bold text-[var(--text)] tracking-wide">
            Recovered Spend by Anomaly Cause
          </h3>
          <p className="text-xs text-[var(--text-3)] mt-0.5">
            Deterministic attribution aggregated from immutable audit ledger entries
          </p>
        </div>
        <div className="px-2.5 py-1 rounded-[7px] bg-[var(--surface-2)] border border-[var(--line-soft)] text-xs text-[var(--text-2)] font-mono">
          {causes.length} Active Rules
        </div>
      </div>

      <div className="space-y-4 pt-1">
        {causes.map((cause) => {
          const pct = Math.min(100, Math.max(8, (cause.amount_inr / maxAmount) * 100));

          return (
            <div key={cause.label} className="group">
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-[var(--text)] font-medium truncate max-w-[280px]">
                  {cause.label}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-[var(--text-3)] font-mono text-[11px]">
                    {cause.count} {cause.count === 1 ? "remediation" : "remediations"}
                  </span>
                  <span className="font-mono font-semibold text-[var(--mint)]">
                    {formatINR(cause.amount_inr)}
                  </span>
                </div>
              </div>

              {/* Bar track */}
              <div className="h-2 w-full bg-[var(--surface-2)] border border-[var(--line-soft)] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[var(--mint)] rounded-full transition-all duration-500 ease-out group-hover:brightness-110"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}

        {causes.length === 0 && (
          <div className="py-6 text-center text-xs text-[var(--text-3)]">
            No remediation causes recorded yet.
          </div>
        )}
      </div>
    </div>
  );
};
