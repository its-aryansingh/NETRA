"use client";

import { useEffect, useState } from "react";

/**
 * Animate a numeric value over a duration (default 400ms) with ease-out cubic easing.
 * Respects the user's `prefers-reduced-motion` setting by updating instantly.
 */
export function useCountUp(value: number, duration: number = 400): number {
  const [displayValue, setDisplayValue] = useState<number>(value);

  useEffect(() => {
    // Respect reduced-motion preferences
    if (
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setDisplayValue(value);
      return;
    }

    const startValue = displayValue;
    const diff = value - startValue;
    if (diff === 0) return;

    let startTimestamp: number | null = null;
    let animationFrameId: number;

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const elapsed = timestamp - startTimestamp;
      const progress = Math.min(elapsed / duration, 1);
      
      // Ease-out cubic: 1 - (1 - t)^3
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = startValue + diff * easeOut;
      setDisplayValue(current);

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(step);
      } else {
        setDisplayValue(value);
      }
    };

    animationFrameId = requestAnimationFrame(step);

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, [value, duration]);

  return displayValue;
}
