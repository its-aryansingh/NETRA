"use client";

import { useState } from "react";
import { formatINR, formatUSD } from "@/lib/format";
import { simulateRunaway } from "@/lib/api";

interface BurnHeroProps {
  burnInrHour: number;
  baselineInrHour: number;
  multiple: number;
  creditsRemainingUsd: number;
  creditsInitialUsd?: number;
  runwayHours: number;
  selectedRange: "6h" | "24h" | "7d";
  onRangeChange: (r: "6h" | "24h" | "7d") => void;
  onSimulate?: () => void;
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
  onSimulate,
}: BurnHeroProps) {
  const [isSimulating, setIsSimulating] = useState(false);

  const handleSimulate = async () => {
    setIsSimulating(true);
    await simulateRunaway();
    if (onSimulate) onSimulate();
    setTimeout(() => setIsSimulating(false), 500);
  };

  const isAboveBaseline = multiple > 1.2;

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-6 mb-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        {/* Left: Burn Rate & Multiple */}
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--text-3)] font-mono mb-1">
            Current Spend Rate · ap-south-1
          </div>
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="font-mono text-[46px] leading-none font-semibold text-[var(--ember)]">
              {formatINR(burnInrHour)}
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
                Baseline Normal ({formatINR(baselineInrHour)}/hr)
              </span>
            )}
          </div>
        </div>

        {/* Center: Credit Runway with Visual Gauge */}
        <div className="bg-[var(--surface-2)] border border-[var(--line-soft)] rounded-[9px] p-3.5 sm:min-w-[280px]">
          <div className="flex items-center justify-between text-xs mb-1.5 font-mono">
            <span className="text-[var(--text-3)]">Credit Runway</span>
            <span className="text-[var(--text)] font-semibold">{runwayHours}h remaining</span>
          </div>
          {/* Gauge Meter */}
          <div className="w-full bg-[var(--ground)] h-2 rounded-full overflow-hidden border border-[var(--line-soft)]">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                runwayHours < 24 ? "bg-[var(--alarm)]" : runwayHours < 72 ? "bg-[var(--amber)]" : "bg-[var(--mint)]"
              }`}
              style={{ width: `${Math.min(100, Math.max(5, (creditsRemainingUsd / (creditsInitialUsd || 200)) * 100))}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-[11px] text-[var(--text-3)] font-mono mt-1.5">
            <span>{formatUSD(creditsRemainingUsd)} of {formatUSD(creditsInitialUsd)}</span>
            <span>Empty in ~{Math.round(runwayHours)}h</span>
          </div>
        </div>

        {/* Right: Controls & Range Selector */}
        <div className="flex items-center gap-3">
          {/* Time range pills */}
          <div className="flex bg-[var(--surface-2)] p-1 rounded-[9px] border border-[var(--line)]">
            {(["6h", "24h", "7d"] as const).map(range => (
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

          {/* Simulate Runaway Instance Button */}
          <button
            onClick={handleSimulate}
            disabled={isSimulating}
            className="flex items-center gap-2 px-3.5 py-2 rounded-[9px] bg-[var(--ember-bg)] hover:bg-[var(--ember-line)] text-[var(--ember)] text-xs font-medium border border-[var(--ember-line)] transition-colors min-h-[44px]"
            title="Inject a runaway c5.4xlarge compute spike on camera"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
            <span>{isSimulating ? "Spiking..." : "Simulate runaway"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
