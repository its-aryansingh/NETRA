interface TraceStep {
  tool: string;
  ms: number;
  span_id?: string;
}

interface AgentTraceProps {
  traces?: TraceStep[];
}

export default function AgentTrace({ traces = [] }: AgentTraceProps) {
  if (!traces || traces.length === 0) return null;

  const totalMs = traces.reduce((acc, t) => acc + t.ms, 0);
  const maxMs = Math.max(...traces.map(t => t.ms), 1);

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--text)] font-display">
            Agent Execution Trace
          </h3>
          <p className="text-xs text-[var(--text-3)] font-mono">
            OpenTelemetry span export · Strands tool duration breakdown
          </p>
        </div>
        <div className="px-2.5 py-1 rounded-[7px] bg-[var(--surface-2)] border border-[var(--line-soft)] text-xs font-mono text-[var(--mint)]">
          Total: {totalMs} ms
        </div>
      </div>

      <div className="space-y-3 font-mono text-xs">
        {traces.map((step, i) => {
          const widthPct = Math.max(8, Math.round((step.ms / maxMs) * 100));
          return (
            <div key={i} className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="text-[var(--text)] font-medium">{step.tool}</span>
                  {step.span_id && (
                    <span className="text-[var(--text-3)] text-[10px]">
                      [{step.span_id}]
                    </span>
                  )}
                </div>
                <span className="text-[var(--text-3)]">{step.ms} ms</span>
              </div>

              {/* Proportional Duration Bar */}
              <div className="w-full bg-[var(--ground)] h-1.5 rounded-full overflow-hidden border border-[var(--line-soft)]">
                <div
                  className="h-full rounded-full bg-[var(--mint)] transition-all duration-300"
                  style={{ width: `${widthPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
