"use client";

import { formatINR, formatUSD } from "@/lib/format";
import { useCountUp } from "@/lib/useCountUp";

interface BurnHeroProps {
  burnInrHour: number | null | undefined;
  baselineInrHour: number;
  multiple: number;
  creditsRemainingUsd: number;
  creditsInitialUsd?: number;
  runwayHours: number;
  selectedRange: "6h" | "24h" | "7d";
  onRangeChange: (r: "6h" | "24h" | "7d") => void;
  isUnreachable?: boolean;
}

export default function BurnHero({
  burnInrHour,
  baselineInrHour,
  multiple,
  creditsRemainingUsd,
  creditsInitialUsd = 200.0,
  runwayHours,
  selectedRange,
  onRangeChange,
  isUnreachable = false,
}: BurnHeroProps) {
  const animatedBurn = useCountUp(burnInrHour ?? 0, 400);
  const isAboveBaseline = multiple > 1.2;

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-6 mb-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        {/* Left: Burn Rate & Multiple */}
        <div>
          <div className="text-[11px] uppercase tracking-[0.09em] text-[var(--text-3)] font-mono mb-1">
            Live burn rate
          </div>

          {isUnreachable || burnInrHour === null || burnInrHour === undefined ? (
            <div>
              <div className="font-mono text-[46px] leading-none font-semibold text-[var(--text-3)]">
                —
              </div>
              <div className="text-xs text-[var(--alarm)] font-mono mt-1">
                Cannot reach the API
              </div>
            </div>
          ) : (
            <div className="flex items-baseline gap-3 flex-wrap">
              <span className="font-mono text-[46px] leading-none font-semibold text-[var(--ember)]">
                {formatINR(animatedBurn)}
              </span>
              <span className="text-[var(--text-3)] font-mono text-sm">/ hour</span>

              {/* Multiple Over Baseline Chip */}
              {isAboveBaseline ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-[7px] bg-[var(--ember-bg)] border border-[var(--ember-line)] text-xs font-mono text-[var(--ember)] font-medium">
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                    <path d="m18 15-6-6-6 6" />
                  </svg>
                  {multiple}× baseline ({formatINR(baselineInrHour)}/hr)
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-[7px] bg-[var(--mint-bg)] border border-[var(--mint-line)] text-xs font-mono text-[var(--mint)] font-medium">
                  Baseline nominal ({formatINR(baselineInrHour)}/hr)
                </span>
              )}
            </div>
          )}
        </div>

        {/* Center: Credit Runway with Visual Gauge */}
        <div className="bg-[var(--surface-2)] border border-[var(--line-soft)] rounded-[9px] p-3.5 sm:min-w-[280px]">
          <div className="flex items-center justify-between text-xs mb-1.5 font-mono">
            <span className="text-[var(--text-3)]">Credit runway</span>
            <span className="text-[var(--text)] font-semibold">{Math.round(runwayHours)}h remaining</span>
          </div>
          {/* Gauge Meter: based strictly on credits_remaining_usd / credits_initial_usd ($200 default) */}
          <div className="w-full bg-[var(--ground)] h-2 rounded-full overflow-hidden border border-[var(--line-soft)]">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                runwayHours < 24 ? "bg-[var(--alarm)]" : runwayHours < 72 ? "bg-[var(--amber)]" : "bg-[var(--mint)]"
              }`}
              style={{
                width: `${Math.min(100, Math.max(0, (creditsRemainingUsd / (creditsInitialUsd || 200)) * 100))}%`,
              }}
            />
          </div>
          <div className="flex items-center justify-between text-[11px] text-[var(--text-3)] font-mono mt-1.5">
            <span>{formatUSD(creditsRemainingUsd)} of {formatUSD(creditsInitialUsd)}</span>
            <span>Empty in ~{Math.round(runwayHours)}h</span>
          </div>
        </div>

        {/* Right: Range Selector (Surface-2, text-3, text only when selected; no ember) */}
        <div className="flex items-center gap-3">
          <div className="flex bg-[var(--surface-2)] p-1 rounded-[9px] border border-[var(--line)]">
            {(["6h", "24h", "7d"] as const).map((range) => (
              <button
                key={range}
                onClick={() => onRangeChange(range)}
                className={`px-3 py-1 text-xs font-mono rounded-[7px] transition-colors ${
                  selectedRange === range
                    ? "bg-[var(--surface)] text-[var(--text)] font-medium border border-[var(--line)]"
                    : "text-[var(--text-3)] hover:text-[var(--text-2)]"
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
