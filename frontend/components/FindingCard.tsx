import Link from "next/link";
import { formatAge, formatINR } from "@/lib/format";
import { FindingItem } from "@/lib/demo-data";

interface FindingCardProps {
  finding: FindingItem;
}

export default function FindingCard({ finding }: FindingCardProps) {
  const sevBadge = {
    critical: "bg-[var(--alarm)]/10 text-[var(--alarm)] border-[var(--alarm)]/30",
    warning: "bg-[var(--amber)]/10 text-[var(--amber)] border-[var(--amber)]/30",
    info: "bg-[var(--text-3)]/10 text-[var(--text-2)] border-[var(--line)]",
  }[finding.severity];

  const now = Math.floor(Date.now() / 1000);
  const ageSec = Math.max(0, now - finding.detected_at);

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[12px] p-4 animate-fade-rise hover:border-[var(--line-soft)] transition-colors">
      <div className="flex items-center justify-between mb-2">
        <span className={`px-2 py-0.5 rounded-[5px] text-[10px] uppercase font-bold font-mono border ${sevBadge}`}>
          {finding.severity}
        </span>
        <span className="text-[11px] font-mono text-[var(--text-3)]">
          {formatAge(ageSec)} ago
        </span>
      </div>

      <h4 className="text-xs font-semibold text-[var(--text)] line-clamp-2 mb-2 leading-snug">
        {finding.headline || `${finding.resource.sub_type} spend anomalous`}
      </h4>

      <div className="flex items-baseline justify-between font-mono my-2 text-xs">
        <span className="text-[var(--text-3)]">Spend:</span>
        <span className="text-[var(--ember)] font-semibold">
          {formatINR(finding.computed.inr_hour)}/hr
        </span>
      </div>

      <div className="flex items-baseline justify-between font-mono mb-3 text-xs">
        <span className="text-[var(--text-3)]">Impact:</span>
        <span className="text-[var(--text-2)]">
          {finding.computed.multiple}× baseline ({finding.computed.share_of_burn_pct}%)
        </span>
      </div>

      <Link
        href={`/investigations/${finding.finding_id}`}
        className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-[7px] bg-[var(--surface-2)] hover:bg-[var(--line)] text-xs font-medium text-[var(--text)] border border-[var(--line)] transition-colors min-h-[44px]"
      >
        <span>Inspect & Remediate</span>
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M5 12h14" />
          <path d="m12 5 7 7-7 7" />
        </svg>
      </Link>
    </div>
  );
}
