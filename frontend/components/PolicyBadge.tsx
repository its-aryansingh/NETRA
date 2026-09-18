"use client";

interface PolicyBadgeProps {
  ruleId: string;
  reason: string;
}

export default function PolicyBadge({ ruleId, reason }: PolicyBadgeProps) {
  return (
    <div className="w-full rounded-[9px] bg-[var(--alarm-bg)] border border-[var(--alarm-line)] p-3.5 text-left font-mono">
      <div className="flex items-center gap-2 text-[11px] font-semibold text-[var(--alarm)] uppercase tracking-wider">
        <svg
          className="w-4 h-4 shrink-0"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <span>Policy denial · {ruleId}</span>
      </div>
      <p className="text-xs text-[var(--text-2)] leading-relaxed mt-1.5">
        {reason}
      </p>
    </div>
  );
}
