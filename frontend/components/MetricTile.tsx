interface MetricTileProps {
  label: string;
  value: string | number;
  subtitle: string;
  variant?: "default" | "mint" | "ember" | "alarm";
}

export default function MetricTile({
  label,
  value,
  subtitle,
  variant = "default",
}: MetricTileProps) {
  const valueColor = {
    default: "text-[var(--text)]",
    mint: "text-[var(--mint)]",
    ember: "text-[var(--ember)]",
    alarm: "text-[var(--alarm)]",
  }[variant];

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[12px] p-5 flex flex-col justify-between">
      <div className="mb-2">
        <span className="text-[11px] uppercase tracking-[0.09em] text-[var(--text-3)] font-mono">
          {label}
        </span>
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
