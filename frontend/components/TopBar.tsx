"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import useSWR from "swr";
import { getSummary, isDemoMode, setDemoMode, getConnectedAwsAccount } from "@/lib/api";
import { useEffect, useState } from "react";
import WellArchitectedModal from "@/components/WellArchitectedModal";
import AwsConnectModal from "@/components/AwsConnectModal";

export default function TopBar() {
  const pathname = usePathname();
  const [demo, setDemo] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAwsModalOpen, setIsAwsModalOpen] = useState(false);
  const [connectedAccount, setConnectedAccount] = useState<{ accountId: string; region: string } | null>(null);

  const { data: summary } = useSWR("/summary", getSummary, {
    refreshInterval: 5000,
    keepPreviousData: true,
    revalidateOnFocus: false,
  });

  useEffect(() => {
    setDemo(isDemoMode());
    setConnectedAccount(getConnectedAwsAccount());
  }, []);

  const toggleDemo = () => {
    const nextVal = !demo;
    setDemoMode(nextVal);
    setDemo(nextVal);
  };

  const collectorAgeS = summary?.collector_age_s;
  const isStale = collectorAgeS != null && collectorAgeS > 180;

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
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-3 py-1.5 rounded-[7px] text-xs font-medium transition-colors text-[var(--text-2)] hover:text-[var(--text)] hover:bg-[var(--surface)] flex items-center gap-1.5"
              title="AWS Well-Architected 6-Pillar & Formal Verification Inspector"
            >
              <svg className="w-3.5 h-3.5 text-[var(--mint)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              <span>Well-Architected</span>
            </button>
          </nav>
        </div>

        <WellArchitectedModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
        <AwsConnectModal isOpen={isAwsModalOpen} onClose={() => setIsAwsModalOpen(false)} />

        {/* Right side status items */}
        <div className="flex items-center gap-3">
          {/* Stale or Nominal Collector status pill */}
          {isStale ? (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-[7px] bg-[var(--amber-bg)] border border-[var(--amber-line)] text-xs text-[var(--amber)] font-mono">
              <span className="relative flex h-2 w-2">
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--amber)]"></span>
              </span>
              <span>Collector last ran {Math.round(collectorAgeS / 60)}m ago</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-[7px] bg-[var(--surface)] border border-[var(--line)] text-xs text-[var(--text-2)]">
              <span className="relative flex h-2 w-2">
                <span className="animate-pulse-dot absolute inline-flex h-full w-full rounded-full bg-[var(--mint)] opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--mint)]"></span>
              </span>
              <span className="font-mono text-[11px] text-[var(--text-3)]">
                collector · {collectorAgeS != null ? `${collectorAgeS}s ago` : "12s ago"}
              </span>
            </div>
          )}

          {/* Target Region Chip */}
          <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-[7px] bg-[var(--ground)] border border-[var(--line-soft)] text-xs text-[var(--text-3)] font-mono">
            <span>ap-south-1</span>
          </div>

          {/* Connect AWS Account Button */}
          <button
            onClick={() => setIsAwsModalOpen(true)}
            className={`px-2.5 py-1 rounded-[7px] text-[11px] font-mono transition-colors flex items-center gap-1.5 border ${
              !demo
                ? "bg-[var(--mint-bg)] text-[var(--mint)] border-[var(--mint-line)]"
                : "bg-[var(--surface-2)] text-[var(--text-2)] hover:text-[var(--text)] border-[var(--line)]"
            }`}
            title="Connect or manage your live AWS account connection"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
            </svg>
            <span>{!demo ? (connectedAccount?.accountId ? `AWS: ${connectedAccount.accountId}` : "LIVE AWS") : "Connect AWS"}</span>
          </button>

          {/* Demo Mode Toggle Chip */}
          <button
            onClick={() => {
              if (demo) {
                setIsAwsModalOpen(true);
              } else {
                toggleDemo();
              }
            }}
            title="Click to toggle demo / live AWS mode"
            className="px-2.5 py-1 rounded-[7px] text-[11px] font-mono transition-colors bg-[var(--surface-2)] border border-[var(--line)] text-[var(--text-3)]"
          >
            {demo ? "demo data" : "live aws"}
          </button>
        </div>
      </div>
    </header>
  );
}
