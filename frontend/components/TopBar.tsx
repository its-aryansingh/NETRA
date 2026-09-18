"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { isDemoMode, setDemoMode } from "@/lib/api";
import { useEffect, useState } from "react";

export default function TopBar() {
  const pathname = usePathname();
  const [demo, setDemo] = useState(true);

  useEffect(() => {
    setDemo(isDemoMode());
  }, []);

  const toggleDemo = () => {
    setDemoMode(!demo);
    setDemo(!demo);
  };

  return (
    <header className="w-full border-b border-[var(--line)] bg-[var(--surface-2)]/90 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Brand & Eye Mark */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 group">
            {/* Third Eye Instrument Logo */}
            <svg
              className="w-5 h-5 text-[var(--ember)] transition-transform group-hover:scale-105"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
              <circle cx="12" cy="12" r="3" />
              <line x1="12" y1="1" x2="12" y2="3" />
            </svg>
            <span
              className="font-display font-bold text-lg text-[var(--text)] tracking-[0.14em]"
              style={{ letterSpacing: "0.14em" }}
            >
              NETRA
            </span>
          </Link>

          {/* Nav Links */}
          <nav className="flex items-center gap-1">
            <Link
              href="/"
              className={`px-3 py-1.5 rounded-[7px] text-xs font-medium transition-colors ${
                pathname === "/"
                  ? "bg-[var(--surface)] text-[var(--text)] border border-[var(--line)]"
                  : "text-[var(--text-2)] hover:text-[var(--text)] hover:bg-[var(--surface)]"
              }`}
            >
              Overview
            </Link>
            <Link
              href="/audit"
              className={`px-3 py-1.5 rounded-[7px] text-xs font-medium transition-colors ${
                pathname === "/audit"
                  ? "bg-[var(--surface)] text-[var(--text)] border border-[var(--line)]"
                  : "text-[var(--text-2)] hover:text-[var(--text)] hover:bg-[var(--surface)]"
              }`}
            >
              Audit Ledger
            </Link>
          </nav>
        </div>

        {/* Right side status items */}
        <div className="flex items-center gap-3">
          {/* Live collector status pill with pulsing dot */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-[7px] bg-[var(--surface)] border border-[var(--line)] text-xs text-[var(--text-2)]">
            <span className="relative flex h-2 w-2">
              <span className="animate-pulse-dot absolute inline-flex h-full w-full rounded-full bg-[var(--mint)] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--mint)]"></span>
            </span>
            <span className="font-mono text-[11px] uppercase tracking-wider">Collector 1m</span>
          </div>

          {/* Target Region Chip */}
          <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-[7px] bg-[var(--ground)] border border-[var(--line-soft)] text-xs text-[var(--text-3)] font-mono">
            <span>ap-south-1</span>
          </div>

          {/* Demo Mode Toggle Chip */}
          <button
            onClick={toggleDemo}
            title="Click to toggle Demo Mode"
            className={`px-2.5 py-1 rounded-[7px] text-xs font-mono transition-colors border ${
              demo
                ? "bg-[var(--amber)]/10 text-[var(--amber)] border-[var(--amber)]/30"
                : "bg-[var(--surface)] text-[var(--text-3)] border-[var(--line)]"
            }`}
          >
            {demo ? "DEMO: ON" : "LIVE AWS"}
          </button>
        </div>
      </div>
    </header>
  );
}
