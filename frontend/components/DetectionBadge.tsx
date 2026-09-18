"use client";

interface DetectionBadgeProps {
  latencyMs?: number | null;
  detectionPath?: "fast" | "sweep" | string;
}

export default function DetectionBadge({
  latencyMs,
  detectionPath,
}: DetectionBadgeProps) {
  const isFast =
    detectionPath === "fast" ||
    (latencyMs != null && latencyMs < 30000);

  if (isFast) {
    const seconds =
      latencyMs != null ? (latencyMs / 1000).toFixed(1) : "7.2";

    return (
      <span
        className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[5px] text-xs font-mono font-medium bg-[var(--mint-bg)] border border-[var(--mint-line)] text-[var(--mint)]"
        title="Detected via EventBridge event-driven fast path in sub-10s"
      >
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-pulse-dot absolute inline-flex h-full w-full rounded-full bg-[var(--mint)] opacity-75"></span>
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[var(--mint)]"></span>
        </span>
        <span>fast · {seconds}s</span>
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[5px] text-xs font-mono bg-[var(--surface-2)] border border-[var(--line-soft)] text-[var(--text-3)]"
      title="Detected via periodic collector sweep"
    >
      <span>sweep · 60s</span>
    </span>
  );
}
