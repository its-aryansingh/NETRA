import { formatAge, formatINR } from "@/lib/format";
import { PricedResourceItem } from "@/lib/demo-data";

interface InventoryTableProps {
  resources: PricedResourceItem[];
  isLoading?: boolean;
}

function Sparkline({ history }: { history?: number[] }) {
  if (!history || history.length < 3) {
    return <span className="text-[var(--text-3)]">—</span>;
  }

  const minVal = Math.min(...history);
  const maxVal = Math.max(...history);
  const first = history[0];
  const last = history[history.length - 1];

  let strokeColor = "var(--text-3)";
  if (first > 0) {
    const pctChange = (last - first) / first;
    if (pctChange > 0.05) strokeColor = "var(--ember)";
    else if (pctChange < -0.05) strokeColor = "var(--mint)";
  } else if (last > 0) {
    strokeColor = "var(--ember)";
  }

  const points = history
    .map((val, idx) => {
      const x = ((idx / (history.length - 1)) * 64).toFixed(1);
      const y = (maxVal === minVal ? 10 : 18 - ((val - minVal) / (maxVal - minVal)) * 16).toFixed(1);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div
      className="inline-flex items-center justify-center w-full"
      title={`1h spend trend: ₹${first.toFixed(2)} → ₹${last.toFixed(2)}/hr`}
    >
      <svg
        width="64"
        height="20"
        viewBox="0 0 64 20"
        className="overflow-visible inline-block"
      >
        <polyline
          fill="none"
          stroke={strokeColor}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points}
        />
      </svg>
    </div>
  );
}

export default function InventoryTable({
  resources,
  isLoading = false,
}: InventoryTableProps) {
  if (isLoading) {
    return (
      <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-5">
        <div className="h-6 w-48 bg-[var(--surface-2)] rounded animate-pulse mb-4" />
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-10 bg-[var(--surface-2)] rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--text)] font-display">
            Live priced inventory
          </h3>
        </div>
        <div className="text-xs font-mono text-[var(--text-3)]">
          {resources.length} billable resources
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-[var(--line)] text-[var(--text-3)] uppercase tracking-[0.09em] text-[11px]">
              <th className="pb-3 font-medium">Kind</th>
              <th className="pb-3 font-medium">Resource ID</th>
              <th className="pb-3 font-medium">Sub Type</th>
              <th className="pb-3 font-medium">State</th>
              <th className="pb-3 font-medium">Age</th>
              <th className="pb-3 font-medium">Util</th>
              <th className="pb-3 font-medium text-center w-[72px]" title="1-hour spend trend">1h</th>
              <th className="pb-3 font-medium text-right">Spend Rate</th>
              <th className="pb-3 font-medium pl-4">Hashed Provenance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--line-soft)]">
            {resources.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-8 text-center text-[var(--text-3)]">
                  No billable resources running. Nothing to price.
                </td>
              </tr>
            ) : (
              resources.map((res) => {
                const isHashed = res.price_ref && res.price_ref.startsWith("sha256:");
                const hashShort = isHashed ? res.price_ref.replace("sha256:", "").slice(0, 12) : null;

                return (
                  <tr key={res.resource_id} className="hover:bg-[var(--surface-2)]/50 transition-colors">
                    <td className="py-3 text-[var(--text-2)] capitalize">{res.kind}</td>
                    <td className="py-3 text-[var(--text)] font-medium">
                      <div className="flex items-center gap-1.5">
                        <span>{res.resource_id}</span>
                        {res.tags?.["netra:protected"] && (
                          <span className="text-[10px] bg-[var(--amber)]/10 text-[var(--amber)] px-1.5 py-0.2 rounded border border-[var(--amber)]/30">
                            protected
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 text-[var(--text-2)]">{res.sub_type}</td>
                    <td className="py-3">
                      <span className="inline-flex items-center gap-1.5 text-[var(--mint)]">
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--mint)]"></span>
                        {res.state}
                      </span>
                    </td>
                    <td className="py-3 text-[var(--text-3)]">
                      {formatAge(res.age_seconds)}
                    </td>
                    <td className="py-3 text-[var(--text-3)]">
                      {res.util ?? "—"}
                    </td>
                    <td className="py-3 w-[72px] text-center">
                      <Sparkline history={res.history} />
                    </td>
                    <td className="py-3 text-right font-semibold text-[var(--text)]">
                      {formatINR(res.inr_hour)}/hr
                    </td>
                    <td className="py-3 pl-4">
                      {isHashed ? (
                        <span
                          className="inline-flex items-center gap-1 text-[11px] text-[var(--mint)] bg-[var(--mint-bg)] border border-[var(--mint-line)] px-1.5 py-0.5 rounded cursor-help"
                          title={`Verified SHA-256 Provenance:\n${res.price_ref}\nDirect cryptographic hash of official AWS Pricing API payload.`}
                        >
                          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                          <span>sha256:{hashShort}…</span>
                        </span>
                      ) : (
                        <span
                          className="text-[11px] text-[var(--text-3)] bg-[var(--surface-2)] border border-[var(--line-soft)] px-1.5 py-0.5 rounded cursor-help"
                          title="Fallback price model applied (API offline or throttled)"
                        >
                          fallback:{res.sub_type}
                        </span>
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
