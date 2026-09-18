"use client";

import { useState } from "react";
import { simulateRunaway } from "@/lib/api";

interface DemoControlsProps {
  onSimulate?: () => void;
}

export default function DemoControls({ onSimulate }: DemoControlsProps) {
  const [isSimulating, setIsSimulating] = useState(false);

  // Gated strictly on process.env.NEXT_PUBLIC_DEMO === "1"
  if (process.env.NEXT_PUBLIC_DEMO !== "1") {
    return null;
  }

  const handleSimulate = async () => {
    setIsSimulating(true);
    try {
      await simulateRunaway();
      if (onSimulate) {
        onSimulate();
      }
    } catch (err) {
      console.error("Simulation failed:", err);
    } finally {
      setTimeout(() => setIsSimulating(false), 500);
    }
  };

  return (
    <div className="w-full mt-8 py-3 px-4 rounded-[10px] bg-[var(--surface-2)]/60 border border-[var(--line)] flex items-center justify-between gap-4">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.09em] text-[var(--text-3)] font-mono">
        <span className="w-2 h-2 rounded-full bg-[var(--amber)] opacity-75" />
        <span>Demo controls · fixture data</span>
      </div>

      <button
        onClick={handleSimulate}
        disabled={isSimulating}
        className="px-3 py-1.5 rounded-[7px] bg-transparent hover:bg-[var(--surface)] text-[var(--text-2)] hover:text-[var(--text)] text-xs font-mono border border-[var(--line)] transition-colors min-h-[36px] flex items-center gap-2"
        title="Inject runaway instance spend spike"
      >
        <svg
          className="w-3.5 h-3.5 text-[var(--text-3)]"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
        <span>{isSimulating ? "Injecting spike..." : "Simulate runaway"}</span>
      </button>
    </div>
  );
}
