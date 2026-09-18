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
            Live Priced Inventory
          </h3>
          <p className="text-xs text-[var(--text-3)] font-mono">
            Every resource priced deterministically against AWS Price List documents
          </p>
        </div>
        <div className="text-xs font-mono text-[var(--text-3)]">
          {resources.length} billable resources
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-[var(--line)] text-[var(--text-3)] uppercase tracking-wider text-[11px]">
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
                  Nothing burning above baseline. Collector last ran 12s ago.
                </td>
              </tr>
            ) : (
              resources.map(res => {
                const isVerified = res.price_ref.startsWith("sha256:");
                const shortRef = isVerified
                  ? `sha256:${res.price_ref.slice(7, 15)}...`
                  : res.price_ref;

                return (
                  <tr key={res.resource_id} className="hover:bg-[var(--surface-2)]/50 transition-colors">
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded-[5px] text-[10px] uppercase font-bold bg-[var(--surface-2)] text-[var(--text-2)] border border-[var(--line-soft)]">
                        {res.kind}
                      </span>
                    </td>
                    <td className="py-3 text-[var(--text)] font-medium">
                      {res.resource_id}
                      {res.tags?.["netra:protected"] && (
                        <span className="ml-1.5 px-1.5 py-0.5 rounded text-[9px] bg-[var(--amber)]/10 text-[var(--amber)] border border-[var(--amber)]/20">
                          protected
                        </span>
                      )}
                    </td>
                    <td className="py-3 text-[var(--text-2)]">{res.sub_type}</td>
                    <td className="py-3">
                      <span className="inline-flex items-center gap-1.5 text-[var(--text-2)]">
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            res.state === "running" ? "bg-[var(--mint)]" : "bg-[var(--text-3)]"
                          }`}
                        />
                        {res.state}
                      </span>
                    </td>
                    <td className="py-3 text-[var(--text-3)]">{formatAge(res.age_seconds)}</td>
                    <td className="py-3 text-right text-[var(--ember)] font-semibold">
                      {formatINR(res.inr_hour)}/hr
                    </td>
                    <td className="py-3 pl-4">
                      <span
                        title={res.price_ref}
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[5px] text-[11px] border ${
                          isVerified
                            ? "bg-[var(--mint-bg)] text-[var(--mint)] border-[var(--mint-line)]"
                            : "bg-[var(--amber)]/10 text-[var(--amber)] border-[var(--amber)]/30"
                        }`}
                      >
                        {isVerified ? (
                          <svg className="w-3 h-3 text-[var(--mint)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                          </svg>
                        ) : (
                          <svg className="w-3 h-3 text-[var(--amber)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <line x1="12" y1="8" x2="12" y2="12" />
                            <line x1="12" y1="16" x2="12.01" y2="16" />
                          </svg>
                        )}
                        <span>{shortRef}</span>
                      </span>
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
