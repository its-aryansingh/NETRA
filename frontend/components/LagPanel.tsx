"use client";

import React from "react";

export interface ReportedCostData {
  inr_hour?: number;
  usd_hour?: number;
  as_of_epoch?: number;
  staleness_seconds?: number;
  granularity?: "HOURLY" | "DAILY";
  available?: boolean;
  reason?: "not_enabled" | "no_data_yet" | "error" | null | string;
}

interface LagPanelProps {
  reported?: ReportedCostData;
  liveInrHour?: number;
  collectorAgeS?: number;
}

function formatAge(seconds: number): string {
  if (seconds < 60) {
    const s = Math.max(1, Math.floor(seconds));
    return `last updated ${s} ${s === 1 ? "second" : "seconds"} ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `last updated ${minutes} ${minutes === 1 ? "minute" : "minutes"} ago`;
  }
  const hours = Math.floor(seconds / 3600);
  return `last updated ${hours} ${hours === 1 ? "hour" : "hours"} ago`;
}

export default function LagPanel({
  reported,
  liveInrHour = 412.80,
  collectorAgeS = 8,
}: LagPanelProps) {
  const isAvailable = reported?.available ?? true;
  const reportedInr = reported?.inr_hour ?? 18.40;
  const stalenessS = reported?.staleness_seconds ?? 50400;
  const isStaleCritical = stalenessS > 3 * 3600; // Over 3 hours triggers var(--alarm)

  const getUnavailableReasonText = () => {
    switch (reported?.reason) {
      case "not_enabled":
        return "Cost Explorer is not enabled for this account.";
      case "no_data_yet":
        return "AWS has no cost data for this account yet. It can take up to 24 hours.";
      case "error":
      default:
        return "Cost Explorer did not answer.";
    }
  };

  return (
    <div
      className="w-full bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-5 mb-6"
      style={{
        backgroundColor: "var(--surface)",
        borderColor: "var(--line)",
      }}
    >
      <div className="grid grid-cols-1 md:grid-cols-12 gap-y-3 items-center">
        {/* ROW 1: AWS Cost Explorer */}
        <div className="md:col-span-4 text-[13px] text-[var(--text-2)] font-sans">
          AWS Cost Explorer says
        </div>
        <div className="md:col-span-4 font-mono text-[28px] text-[var(--text-3)] tabular-nums leading-none">
          {isAvailable ? (
            <>
              Rs {reportedInr.toFixed(2)} <span className="text-[16px] text-[var(--text-3)] font-sans">/ hr</span>
            </>
          ) : (
            "—"
          )}
        </div>
        <div className="md:col-span-4 md:text-right font-mono text-[12px] tabular-nums">
          {isAvailable ? (
            <span
              className={isStaleCritical ? "text-[var(--alarm)] font-semibold" : "text-[var(--text-3)]"}
              style={{ color: isStaleCritical ? "var(--alarm)" : "var(--text-3)" }}
            >
              {formatAge(stalenessS)}
            </span>
          ) : (
            <span className="text-[var(--text-3)] font-sans">
              {getUnavailableReasonText()}
            </span>
          )}
        </div>

        {/* 1px Divider */}
        <div className="col-span-12 my-1 border-b border-[var(--line-soft)]" />

        {/* ROW 2: NETRA */}
        <div className="md:col-span-4 text-[13px] text-[var(--text-2)] font-sans">
          NETRA says
        </div>
        <div className="md:col-span-4 font-mono text-[28px] text-[var(--ember)] tabular-nums leading-none">
          Rs {liveInrHour.toFixed(2)} <span className="text-[16px] text-[var(--text-2)] font-sans">/ hr</span>
        </div>
        <div className="md:col-span-4 md:text-right font-mono text-[12px] text-[var(--text-3)] tabular-nums">
          {formatAge(collectorAgeS)}
        </div>
      </div>

      {/* Caption Beneath */}
      <div className="mt-3 text-[12.5px] text-[var(--text-2)] font-sans">
        Same account. Same moment.
      </div>
    </div>
  );
}
