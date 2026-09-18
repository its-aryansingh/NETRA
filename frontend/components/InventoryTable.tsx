import { formatAge, formatINR } from "@/lib/format";
import { PricedResourceItem } from "@/lib/demo-data";

interface InventoryTableProps {
  resources: PricedResourceItem[];
  isLoading?: boolean;
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
              <th className="pb-3 font-medium text-right">Spend Rate</th>
              <th className="pb-3 font-medium pl-4">Hashed Provenance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--line-soft)]">
            {resources.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-[var(--text-3)]">
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
