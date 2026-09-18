interface EvidenceChipsProps {
  evidence: Array<{ label: string; value: string }>;
}

export default function EvidenceChips({ evidence }: EvidenceChipsProps) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-5 mb-6">
      <h3 className="text-xs uppercase tracking-wider text-[var(--text-3)] font-mono mb-3">
        Supporting Observability Evidence
      </h3>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 font-mono">
        {evidence.map((ev, i) => (
          <div
            key={i}
            className="bg-[var(--surface-2)] border border-[var(--line-soft)] rounded-[8px] p-2.5"
          >
            <div className="text-[11px] text-[var(--text-3)] truncate mb-1">
              {ev.label}
            </div>
            <div className="text-xs font-semibold text-[var(--text)] truncate">
              {ev.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
