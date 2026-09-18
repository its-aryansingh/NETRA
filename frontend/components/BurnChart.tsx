"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatINR, formatTime } from "@/lib/format";

interface BurnChartProps {
  points: Array<{ ts: number; inr_hour: number }>;
  baselineInrHour: number;
  stepAtTs?: number | null;
}

export default function BurnChart({
  points,
  baselineInrHour,
  stepAtTs,
}: BurnChartProps) {
  const chartData = useMemo(() => {
    return points.map(p => ({
      ...p,
      timeLabel: formatTime(p.ts),
      inr_hour: p.inr_hour,
    }));
  }, [points]);

  const latestPoint = chartData[chartData.length - 1];

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--text)] font-display">
            Expenditure Burn Velocity
          </h3>
          <p className="text-xs text-[var(--text-3)] font-mono">
            Near-real-time expenditure rate computed minute-by-minute
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs font-mono text-[var(--text-3)]">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 bg-[var(--ember)] inline-block"></span>
            <span>Live spend</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 border-b border-dashed border-[var(--text-3)] inline-block"></span>
            <span>Baseline ({formatINR(baselineInrHour)}/hr)</span>
          </div>
        </div>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="burnGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#E9883C" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#E9883C" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <XAxis
              dataKey="timeLabel"
              stroke="#808E88"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "#232C28" }}
              interval="preserveStartEnd"
            />
            <YAxis
              stroke="#808E88"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "#232C28" }}
              tickFormatter={val => `₹${val}`}
            />

            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-[var(--surface-2)] border border-[var(--line)] p-2.5 rounded-[7px] shadow-xl text-xs font-mono">
                      <div className="text-[var(--text-3)] mb-1">{data.timeLabel}</div>
                      <div className="text-[var(--ember)] font-semibold text-sm">
                        {formatINR(data.inr_hour)}/hr
                      </div>
                      <div className="text-[var(--text-3)] text-[11px] mt-0.5">
                        Baseline: {formatINR(baselineInrHour)}/hr
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />

            {/* Dashed baseline line */}
            <ReferenceLine
              y={baselineInrHour}
              stroke="#808E88"
              strokeDasharray="4 4"
              strokeWidth={1}
            />

            {/* Step change marker if detected */}
            {stepAtTs && (
              <ReferenceLine
                x={formatTime(stepAtTs)}
                stroke="#F2555A"
                strokeDasharray="3 3"
                label={{
                  value: "STEP CHANGE",
                  position: "insideTopLeft",
                  fill: "#F2555A",
                  fontSize: 10,
                  fontFamily: "IBM Plex Mono",
                }}
              />
            )}

            <Area
              type="monotone"
              dataKey="inr_hour"
              stroke="#E9883C"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#burnGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
