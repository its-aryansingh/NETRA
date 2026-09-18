import { formatINR } from "@/lib/format";

interface MetricTileProps {
  label: string;
  value: string | number;
  subtitle: string;
  variant?: "default" | "mint" | "ember" | "alarm";
  tag?: string;
}

export default function MetricTile({
  label,
  value,
  subtitle,
  variant = "default",
  tag,
}: MetricTileProps) {
  const valueColor = {
    default: "text-[var(--text)]",
    mint: "text-[var(--mint)]",
    ember: "text-[var(--ember)]",
    alarm: "text-[var(--alarm)]",
  }[variant];

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[12px] p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs uppercase tracking-wider text-[var(--text-3)] font-mono">
          {label}
        </span>
        {tag && (
          <span className="px-2 py-0.5 rounded-[5px] text-[10px] font-mono bg-[var(--surface-2)] text-[var(--text-2)] border border-[var(--line-soft)]">
            {tag}
          </span>
        )}
      </div>

      <div className={`font-mono text-2xl sm:text-3xl font-semibold ${valueColor} my-1`}>
        {value}
      </div>

      <div className="text-xs text-[var(--text-3)] font-mono">
        {subtitle}
      </div>
    </div>
  );
}
