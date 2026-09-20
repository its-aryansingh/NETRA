"use client";

import React, { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { getSummary, getFindings } from "@/lib/api";

const inFormatter = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export default function BurnTape() {
  const { data: summary } = useSWR("/summary", getSummary, {
    refreshInterval: 5000,
    keepPreviousData: true,
  });

  const { data: findingsData } = useSWR("/findings/open", () => getFindings("open"), {
    refreshInterval: 5000,
    keepPreviousData: true,
  });

  const targetBurnRate = summary?.burn_inr_hour ?? 412.80;

  // Mount timestamp for accumulating spend
  const mountedAtRef = useRef<number>(Date.now());
  const accumulatedSpendRef = useRef<number>(0);
  const lastTickTimeRef = useRef<number>(Date.now());

  // Rate easing state
  const currentRateRef = useRef<number>(targetBurnRate);
  const easeStartTimeRef = useRef<number>(Date.now());
  const easeStartRateRef = useRef<number>(targetBurnRate);
  const easeTargetRateRef = useRef<number>(targetBurnRate);

  // Display text state to trigger re-renders only when rendered string changes
  const [displayAmount, setDisplayAmount] = useState<string>("Rs 0.00");
  const [displayRate, setDisplayRate] = useState<string>(`at Rs ${targetBurnRate.toFixed(2)} / hr`);
  const [isFlashing, setIsFlashing] = useState<boolean>(false);

  // Track critical findings for 600ms flash
  const lastCritCountRef = useRef<number>(0);

  // Detect rate change to initiate 400ms easing
  useEffect(() => {
    if (Math.abs(targetBurnRate - easeTargetRateRef.current) > 0.01) {
      easeStartRateRef.current = currentRateRef.current;
      easeTargetRateRef.current = targetBurnRate;
      easeStartTimeRef.current = Date.now();
      setDisplayRate(`at Rs ${targetBurnRate.toFixed(2)} / hr`);
    }
  }, [targetBurnRate]);

  // Flash on new critical finding
  useEffect(() => {
    const critCount = (findingsData?.findings || []).filter(
      (f: any) => f.severity === "critical"
    ).length;

    if (critCount > lastCritCountRef.current && lastCritCountRef.current !== 0) {
      setIsFlashing(true);
      const timer = setTimeout(() => setIsFlashing(false), 600);
      return () => clearTimeout(timer);
    }
    lastCritCountRef.current = critCount;
  }, [findingsData]);

  // RAF loop for accumulation
  useEffect(() => {
    let animId: number;
    let isMounted = true;

    // Check reduced motion preference
    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReducedMotion) {
      const interval = setInterval(() => {
        const now = Date.now();
        const elapsedHours = (now - mountedAtRef.current) / 3_600_000;
        const total = targetBurnRate * elapsedHours;
        const formatted = `Rs ${inFormatter.format(total)}`;
        setDisplayAmount(formatted);
      }, 1000);
      return () => clearInterval(interval);
    }

    const tick = () => {
      if (!isMounted) return;
      const now = Date.now();
      const dt = (now - lastTickTimeRef.current) / 1000;
      lastTickTimeRef.current = now;

      // Ease rate over 400ms
      const easeElapsed = now - easeStartTimeRef.current;
      if (easeElapsed < 400) {
        const progress = easeElapsed / 400;
        // Cubic ease-out
        const t = 1 - Math.pow(1 - progress, 3);
        currentRateRef.current =
          easeStartRateRef.current +
          (easeTargetRateRef.current - easeStartRateRef.current) * t;
      } else {
        currentRateRef.current = easeTargetRateRef.current;
      }

      // Increment accumulated spend: rate in INR/hr / 3600 per second
      accumulatedSpendRef.current += (currentRateRef.current / 3600) * dt;

      const formatted = `Rs ${inFormatter.format(accumulatedSpendRef.current)}`;
      setDisplayAmount((prev) => (prev !== formatted ? formatted : prev));

      animId = requestAnimationFrame(tick);
    };

    lastTickTimeRef.current = Date.now();
    animId = requestAnimationFrame(tick);

    return () => {
      isMounted = false;
      cancelAnimationFrame(animId);
    };
  }, []);

  return (
    <div
      className={`w-full h-[44px] flex items-center justify-between px-4 sm:px-6 border-b transition-colors duration-300 select-none ${
        isFlashing
          ? "bg-[var(--ember-bg)] border-[var(--ember)]"
          : "bg-[var(--surface-2)] border-[var(--line-soft)]"
      }`}
      style={{
        backgroundColor: isFlashing ? "var(--ember-bg)" : "var(--surface-2)",
        borderBottomColor: isFlashing ? "var(--ember)" : "var(--line-soft)",
      }}
      aria-live="off"
    >
      <span className="sr-only">Accumulated spend since page load</span>

      {/* Left: Descriptive Label */}
      <div className="text-[12.5px] text-[var(--text-2)] font-sans">
        Since you opened this page
      </div>

      {/* Centre: Accumulating Meter */}
      <div className="font-mono text-[22px] text-[var(--ember)] font-semibold tabular-nums leading-none tracking-tight">
        {displayAmount}
      </div>

      {/* Right: Instantaneous Hourly Rate */}
      <div className="font-mono text-[12px] text-[var(--text-3)] tabular-nums">
        {displayRate}
      </div>
    </div>
  );
}
