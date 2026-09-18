interface TraceStep {
  tool: string;
  ms: number;
  span_id?: string;
  via?: "direct" | "mcp" | string;
}

interface AgentTraceProps {
  traces?: TraceStep[];
}

export default function AgentTrace({ traces = [] }: AgentTraceProps) {
  if (!traces || traces.length === 0) return null;

  const totalMs = traces.reduce((acc, t) => acc + t.ms, 0);
  const maxMs = Math.max(...traces.map((t) => t.ms), 1);

  const directSteps = traces.filter((t) => t.via !== "mcp");
  const mcpSteps = traces.filter((t) => t.via === "mcp");
  const hasTrustBoundary = directSteps.length > 0 && mcpSteps.length > 0;

  const renderStep = (step: TraceStep, key: any) => {
    const widthPct = Math.max(8, Math.round((step.ms / maxMs) * 100));
    return (
      <div key={key} className="flex flex-col gap-1">
        <div className="flex items-center justify-between text-[11px]">
          <div className="flex items-center gap-2">
            <span className="text-[var(--text)] font-medium">{step.tool}</span>
            {step.span_id && (
              <span className="text-[var(--text-3)] text-[10px]">
                [{step.span_id}]
              </span>
            )}
            {step.via && (
              <span
                className={`text-[9px] px-1.5 py-0.2 rounded border ${
                  step.via === "mcp"
                    ? "bg-[var(--amber)]/10 text-[var(--amber)] border-[var(--amber)]/30"
                    : "bg-[var(--surface-2)] text-[var(--text-3)] border-[var(--line-soft)]"
                }`}
              >
                {step.via}
              </span>
            )}
          </div>
          <span className="text-[var(--text-3)]">{step.ms} ms</span>
        </div>

        {/* Proportional Duration Bar */}
        <div className="w-full bg-[var(--ground)] h-1.5 rounded-full overflow-hidden border border-[var(--line-soft)]">
          <div
            className={`h-full rounded-full transition-all duration-300 ${
              step.via === "mcp" ? "bg-[var(--amber)]" : "bg-[var(--mint)]"
            }`}
            style={{ width: `${widthPct}%` }}
          />
        </div>
      </div>
    );
  };

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
        {directSteps.map((step, i) => renderStep(step, `direct-${i}`))}

        {hasTrustBoundary && (
          <div className="flex items-center gap-3 my-3.5">
            <div className="flex-1 border-t border-[var(--line-soft)]" />
            <span className="text-[11px] font-mono text-[var(--text-3)] uppercase tracking-wider">
              — trust boundary —
            </span>
            <div className="flex-1 border-t border-[var(--line-soft)]" />
          </div>
        )}

        {mcpSteps.map((step, i) => renderStep(step, `mcp-${i}`))}
      </div>
    </div>
  );
}
