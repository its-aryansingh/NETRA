"use client";

import { useEffect, useState, useCallback } from "react";
import BurnHero from "@/components/BurnHero";
import BurnChart from "@/components/BurnChart";
import MetricTile from "@/components/MetricTile";
import InventoryTable from "@/components/InventoryTable";
import FindingCard from "@/components/FindingCard";
import {
  getSummary,
  getBurn,
  getInventory,
  getFindings,
} from "@/lib/api";
import { FindingItem, PricedResourceItem } from "@/lib/demo-data";
import { formatINR } from "@/lib/format";

export default function OverviewPage() {
  const [selectedRange, setSelectedRange] = useState<"6h" | "24h" | "7d">("24h");
  const [summary, setSummary] = useState<any>(null);
  const [burnData, setBurnData] = useState<any>(null);
  const [inventory, setInventory] = useState<PricedResourceItem[]>([]);
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const hoursMap = { "6h": 6, "24h": 24, "7d": 168 };
      const [sum, burn, inv, fnd] = await Promise.all([
        getSummary(),
        getBurn(hoursMap[selectedRange]),
        getInventory(),
        getFindings("open"),
      ]);
      setSummary(sum);
      setBurnData(burn);
      setInventory(inv.resources || []);
      setFindings(fnd.findings || []);
    } catch (err) {
      console.error("Failed to load overview data:", err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedRange]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [loadData]);

  if (isLoading && !summary) {
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
      {summary && (
        <BurnHero
          burnInrHour={summary.burn_inr_hour}
          baselineInrHour={summary.baseline_inr_hour}
          multiple={summary.multiple}
          creditsRemainingUsd={summary.credits_remaining_usd}
          runwayHours={summary.runway_hours}
          selectedRange={selectedRange}
          onRangeChange={setSelectedRange}
          onSimulate={loadData}
        />
      )}

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
              label="Projected Month-End"
              value={formatINR(summary?.projected_month_inr || 0)}
              subtitle="Current burn trajectory"
              variant="default"
              tag="30-day"
            />
            <MetricTile
              label="Prevented Spend"
              value={formatINR(summary?.prevented_today_inr || 0)}
              subtitle="Automated & approved fixes"
              variant="mint"
              tag="Today"
            />
            <MetricTile
              label="Detection Latency"
              value={`${summary?.detection_latency_s || 42}s`}
              subtitle="Cost Explorer: up to 24h"
              variant="ember"
              tag="Real-Time"
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
                  Active Findings
                </h3>
                <p className="text-xs text-[var(--text-3)] font-mono">
                  Autonomous cost agent alerts
                </p>
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
                <h4 className="text-xs font-semibold text-[var(--text)] font-display mb-1">
                  Baseline Expenditure Nominal
                </h4>
                <p className="text-xs text-[var(--text-3)] font-mono">
                  Nothing burning above baseline. Collector last ran 12s ago.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
