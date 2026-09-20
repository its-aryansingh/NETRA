"use client";

import { useState } from "react";
import useSWR from "swr";
import BurnHero from "@/components/BurnHero";
import BurnChart from "@/components/BurnChart";
import MetricTile from "@/components/MetricTile";
import InventoryTable from "@/components/InventoryTable";
import FindingCard from "@/components/FindingCard";
import DemoControls from "@/components/DemoControls";
import {
  getSummary,
  getBurn,
  getInventory,
  getFindings,
} from "@/lib/api";
import { formatINR } from "@/lib/format";
import { useCountUp } from "@/lib/useCountUp";

export default function OverviewPage() {
  const [selectedRange, setSelectedRange] = useState<"6h" | "24h" | "7d">("24h");

  const hoursMap = { "6h": 6, "24h": 24, "7d": 168 };

  const {
    data: summary,
    error: summaryError,
    isLoading: summaryLoading,
    mutate: mutateSummary,
  } = useSWR("/summary", getSummary, {
    refreshInterval: 5000,
    keepPreviousData: true,
    revalidateOnFocus: false,
  });

  const {
    data: burnData,
    mutate: mutateBurn,
  } = useSWR(
    ["/burn", selectedRange],
    () => getBurn(hoursMap[selectedRange]),
    {
      refreshInterval: 5000,
      keepPreviousData: true,
      revalidateOnFocus: false,
    }
  );

  const {
    data: invData,
    mutate: mutateInventory,
  } = useSWR("/inventory", getInventory, {
    refreshInterval: 5000,
    keepPreviousData: true,
    revalidateOnFocus: false,
  });

  const {
    data: fndData,
    mutate: mutateFindings,
  } = useSWR("/findings/open", () => getFindings("open"), {
    refreshInterval: 5000,
    keepPreviousData: true,
    revalidateOnFocus: false,
  });

  const handleRefresh = () => {
    mutateSummary();
    mutateBurn();
    mutateInventory();
    mutateFindings();
  };

  const inventory = invData?.resources || [];
  const findings = fndData?.findings || [];
  const collectorAgeS = summary?.collector_age_s ?? 12;

  // Animated numbers with useCountUp (400ms ease-out cubic)
  const animatedProjected = useCountUp(summary?.projected_month_inr || 0, 400);
  const animatedPrevented = useCountUp(summary?.prevented_today_inr || 0, 400);

  // First load skeleton only
  if (summaryLoading && !summary && !summaryError) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 animate-pulse">
        <div className="h-32 bg-[var(--surface)] border border-[var(--line)] rounded-[14px] mb-6" />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-6">
            <div className="h-72 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="h-28 bg-[var(--surface)] border border-[var(--line)] rounded-[12px]" />
              <div className="h-28 bg-[var(--surface)] border border-[var(--line)] rounded-[12px]" />
              <div className="h-28 bg-[var(--surface)] border border-[var(--line)] rounded-[12px]" />
            </div>
            <div className="h-64 bg-[var(--surface)] border border-[var(--line)] rounded-[14px]" />
          </div>
          <div className="lg:col-span-4 space-y-4">
            <div className="h-44 bg-[var(--surface)] border border-[var(--line)] rounded-[12px]" />
            <div className="h-44 bg-[var(--surface)] border border-[var(--line)] rounded-[12px]" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Burn Hero Unit */}
      <BurnHero
        burnInrHour={summary?.burn_inr_hour}
        baselineInrHour={summary?.baseline_inr_hour ?? 23.04}
        multiple={summary?.multiple ?? 1.0}
        creditsRemainingUsd={summary?.credits_remaining_usd ?? 184.2}
        creditsInitialUsd={summary?.credits_initial_usd ?? 200.0}
        runwayHours={summary?.runway_hours ?? 196}
        selectedRange={selectedRange}
        onRangeChange={setSelectedRange}
        isUnreachable={Boolean(summaryError)}
      />

      {/* Main Grid: 8 Cols (Charts, Metrics, Inventory) + 4 Cols (Anomalies Rail) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Visual Analytics & Resources */}
        <div className="lg:col-span-8 space-y-6">
          {/* Spend Velocity Chart */}
          {burnData && (
            <BurnChart
              points={burnData.points || []}
              baselineInrHour={burnData.baseline_inr_hour || summary?.baseline_inr_hour || 23.04}
              stepAtTs={burnData.step_at_ts}
            />
          )}

          {/* Three Metric Tiles */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricTile
              label="Projected month-end"
              value={formatINR(animatedProjected)}
              subtitle="if nothing changes"
              variant="default"
            />
            <MetricTile
              label="Prevented today"
              value={formatINR(animatedPrevented)}
              subtitle={`${summary?.approved_remediations_count ?? 0} approved remediations`}
              variant="mint"
            />
            <MetricTile
              label="Detection latency"
              value={summary?.detection_latency_s ? `${summary.detection_latency_s}s` : "—"}
              subtitle="Cost Explorer: up to 24h"
              variant="ember"
            />
          </div>

          {/* Priced Inventory Table with Provenance Hashing */}
          <InventoryTable resources={inventory} isLoading={false} />
        </div>

        {/* Right Rail: Active Spend Findings */}
        <div className="lg:col-span-4">
          <div className="sticky top-20 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[var(--line)]">
              <div>
                <h3 className="font-display font-semibold text-sm text-[var(--text)]">
                  Open investigations
                </h3>
              </div>
              <span className="px-2 py-0.5 rounded-[5px] text-xs font-mono font-semibold bg-[var(--surface)] text-[var(--text-2)] border border-[var(--line)]">
                {findings.length}
              </span>
            </div>

            {findings.length > 0 ? (
              <div className="space-y-3">
                {findings.map((finding) => (
                  <FindingCard key={finding.finding_id} finding={finding} />
                ))}
              </div>
            ) : (
              <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[12px] p-6 text-center">
                <svg
                  className="w-8 h-8 text-[var(--mint)] mx-auto mb-2 opacity-80"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <path d="m9 12 2 2 4-4" />
                </svg>
                <p className="text-xs text-[var(--text-3)] font-mono">
                  Nothing burning above baseline. Collector last ran {collectorAgeS}s ago.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Demo Controls at the bottom (gated on NEXT_PUBLIC_DEMO===1) */}
      <DemoControls onSimulate={handleRefresh} />
    </div>
  );
}
